"""Private Supabase Auth session and content-only Data API access."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path.home() / ".config/the-pit/connection.json"


class PitError(Exception):
    pass


class DeliveryUnknown(PitError):
    pass


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, key, method="GET", payload=None, token=None, prefer=None, timeout=60):
    headers = {"apikey": key, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if prefer:
        headers["Prefer"] = prefer
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirects).open(req, timeout=timeout) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        # Response bodies can echo user text or credential details.
        if exc.code >= 500 or exc.code == 408:
            raise DeliveryUnknown("Server outcome is unknown; recover by content hash before retrying") from None
        raise PitError(f"Supabase rejected the request (HTTP {exc.code})") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise DeliveryUnknown("Request outcome is unknown; recover by content hash before retrying") from None


def save_config(config, path=CONFIG):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".connection-")
    try:
        with os.fdopen(fd, "w") as target:
            json.dump(config, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Client:
    def __init__(self, path=CONFIG, timeout=60):
        self.path = path
        self.timeout = timeout
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise PitError("Connection file must be private (mode 0600), not a symlink")
        self.config = json.loads(path.read_text())
        self.base = self.config["url"].rstrip("/")
        if not re.fullmatch(r"https://[a-z0-9]+\.supabase\.co", self.base):
            raise PitError("Unsupported Supabase endpoint")
        self.key = self.config["publishable_key"]
        self.token = self.config["access_token"]

    def ensure_session(self):
        # Serialize rotation across multiple plugin invocations on this Mac.
        import fcntl
        fd = os.open(self.path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            config = json.loads(self.path.read_text())
            if config["user_id"] != self.config["user_id"] or config["url"].rstrip("/") != self.base:
                raise PitError("Connection identity changed during this invocation")
            self.config = config
            if self.config.get("expires_at", 0) <= time.time() + 60:
                session = request(self.base + "/auth/v1/token?grant_type=refresh_token", self.key,
                                  "POST", {"refresh_token": self.config["refresh_token"]}, timeout=self.timeout)
                if session["user"]["id"] != self.config["user_id"]:
                    raise PitError("Refreshed session belongs to another user")
                self.config.update(access_token=session["access_token"],
                                   refresh_token=session["refresh_token"],
                                   expires_at=time.time() + session["expires_in"])
                save_config(self.config, self.path)
            self.token = self.config["access_token"]

    def api(self, path, method="GET", payload=None, prefer=None):
        self.ensure_session()
        return request(self.base + "/rest/v1/" + path, self.key, method, payload, self.token, prefer, timeout=self.timeout)

    def read(self, identity):
        if not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise PitError("Entry identity must be a SHA-256 hash")
        rows = self.api("entries?" + urllib.parse.urlencode({"id": "eq." + identity,
                        "select": "id,received_at,content", "limit": 1}))
        return rows[0] if rows else None

    def append(self, content):
        identity = hashlib.sha256(content.encode("utf-8")).hexdigest()
        rows = self.api("entries?on_conflict=id&select=id,received_at", "POST",
                        {"content": content}, "resolution=ignore-duplicates,return=representation")
        try:
            stored = self.read(identity)
            if not stored or stored["content"] != content:
                raise DeliveryUnknown("Append accepted but exact-text readback failed")
        except PitError:
            raise DeliveryUnknown("Append accepted; readback unresolved. Recover by content hash") from None
        return {"id": identity, "received_at": stored["received_at"],
                "inserted": bool(rows), "uploaded": True, "verified": True}

    def search(self, query, limit=5, context=500):
        if not isinstance(query, str) or not 1 <= len(query) <= 1000 or not 1 <= limit <= 20 or not 0 <= context <= 2000:
            raise PitError("Invalid search parameters")
        return self.api("rpc/pit_search", "POST",
                        {"p_query": query, "p_limit": limit, "p_context": context})

    def read_range(self, identity, start=0, end=1000):
        if not re.fullmatch(r"[a-f0-9]{64}", identity) or not 0 <= start <= end <= 2147483647 or end - start > 20000:
            raise PitError("Invalid range parameters")
        return self.api("rpc/pit_read_range", "POST",
                        {"p_id": identity, "p_start": start, "p_end": end})

    def verify(self, content):
        identity = hashlib.sha256(content.encode("utf-8")).hexdigest()
        stored = self.read(identity)
        if stored is None:
            return {"id": identity, "found": False, "verified": False}
        if stored["content"] != content:
            raise PitError("Stored text does not match the saved snapshot")
        return {"id": identity, "found": True, "verified": True,
                "received_at": stored["received_at"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--append-file", type=Path)
    mode.add_argument("--read")
    mode.add_argument("--search")
    mode.add_argument("--range", nargs=3, metavar=("HASH", "START", "END"))
    mode.add_argument("--verify-file", type=Path)
    mode.add_argument("--status", action="store_true")
    parser.add_argument("--request-timeout", type=float, default=60)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--context", type=int, default=500)
    args = parser.parse_args()
    try:
        if not 0 < args.request_timeout <= 60:
            raise PitError("Request timeout must be between zero and 60 seconds")
        client = Client(timeout=args.request_timeout)
        if args.status:
            client.api("entries?select=id&limit=1")
            result = {"connected": True, "user_id": client.config["user_id"]}
        elif args.read:
            result = client.read(args.read)
        elif args.search is not None:
            result = client.search(args.search, args.limit, args.context)
        elif args.range:
            result = client.read_range(args.range[0], int(args.range[1]), int(args.range[2]))
        elif args.verify_file:
            result = client.verify(args.verify_file.read_bytes().decode("utf-8"))
        else:
            # Decode bytes without newline normalization.
            result = client.append(args.append_file.read_bytes().decode("utf-8"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PitError, OSError, ValueError, KeyError) as exc:
        if not isinstance(exc, PitError):
            exc = PitError("Local connection configuration or input is unavailable/invalid")
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
