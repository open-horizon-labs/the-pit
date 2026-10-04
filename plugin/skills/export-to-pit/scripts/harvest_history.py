"""Incrementally capture visible text from local and configured remote Codex history."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import time

from hosted_client import Client
from transcripts import render_lines


class DeliveryFailure(RuntimeError):
    """An exact pending snapshot could not be verified by the hosted sink."""


def session_files(home: Path):
    for folder in (home / "sessions", home / "archived_sessions"):
        if folder.exists():
            yield from sorted(folder.rglob("*.jsonl"))


def session_metadata(path):
    with path.open("rb") as stream:
        for raw in stream:
            try:
                record = json.loads(raw)
                if record.get("type") == "session_meta":
                    payload = record.get("payload", {})
                    session = payload.get("id") or payload.get("session_id")
                    if isinstance(session, str) and session:
                        return session, payload.get("timestamp") or payload.get("created_at")
            except (ValueError, AttributeError):
                continue
    return None


def checkpoint(path):
    previous_umask = os.umask(0o077)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    finally:
        os.umask(previous_umask)
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS seen (source TEXT NOT NULL, path TEXT NOT NULL, session TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, rendered_hash TEXT NOT NULL, entry_id TEXT NOT NULL, PRIMARY KEY(source, path))")
        db.execute("CREATE TABLE IF NOT EXISTS coverage (source TEXT NOT NULL, session TEXT NOT NULL, details TEXT NOT NULL, PRIMARY KEY(source, session))")
        db.execute("CREATE TABLE IF NOT EXISTS pending (source TEXT NOT NULL, session TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL, PRIMARY KEY(source, session))")
        columns = {row[1] for row in db.execute("PRAGMA table_info(seen)")}
        if "file_hash" in columns and "rendered_hash" not in columns:
            db.execute("ALTER TABLE seen RENAME COLUMN file_hash TO rendered_hash")
        info = list(db.execute("PRAGMA table_info(seen)"))
        primary_key = [row[1] for row in sorted((row for row in info if row[5]), key=lambda row: row[5])]
        if primary_key != ["source", "path"]:
            db.execute("CREATE TABLE seen_new (source TEXT NOT NULL, path TEXT NOT NULL, session TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, rendered_hash TEXT NOT NULL, entry_id TEXT NOT NULL, PRIMARY KEY(source, path))")
            db.execute("INSERT OR REPLACE INTO seen_new SELECT source,path,session,size,mtime_ns,rendered_hash,entry_id FROM seen")
            db.execute("DROP TABLE seen")
            db.execute("ALTER TABLE seen_new RENAME TO seen")
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    return db


def invalidate_on_parser_change(db):
    fingerprint = hashlib.sha256(Path(__file__).with_name("transcripts.py").read_bytes()).hexdigest()
    previous = db.execute("SELECT value FROM metadata WHERE key='renderer_sha256'").fetchone()
    has_seen = db.execute("SELECT 1 FROM seen LIMIT 1").fetchone() is not None
    if (previous and previous[0] != fingerprint) or (previous is None and has_seen):
        # Re-render prior history under the new coverage rules. Exact text hashes
        # still prevent redundant appends when visible text did not change.
        db.execute("UPDATE seen SET mtime_ns=-1")
    db.execute("INSERT INTO metadata VALUES ('renderer_sha256', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (fingerprint,))
    db.commit()


class CompleteLines:
    def __init__(self, stream):
        self.stream = stream
        self.partial = False

    def __iter__(self):
        for row in self.stream:
            if not row.endswith(b"\n"):
                self.partial = True
                return
            yield row


def _save_coverage(db, source, session, coverage):
    db.execute("INSERT INTO coverage VALUES (?, ?, ?) ON CONFLICT(source, session) DO UPDATE SET details=excluded.details", (source, session, json.dumps(coverage, sort_keys=True)))


def queue_delivery(db, source, session, content, metadata):
    db.execute("INSERT INTO pending VALUES (?, ?, ?, ?) ON CONFLICT(source, session) DO NOTHING", (source, session, content, json.dumps(metadata, sort_keys=True)))
    db.commit()


def drain_pending(db, source, client):
    rows = db.execute("SELECT session,content,metadata FROM pending WHERE source=? ORDER BY session", (source,)).fetchall()
    for session, content, metadata_json in rows:
        metadata = json.loads(metadata_json)
        try:
            receipt = client.append(content)
        except Exception:
            raise DeliveryFailure("Hosted Pit delivery remains pending") from None
        if receipt.get("verified") is not True or not receipt.get("id"):
            raise DeliveryFailure("Hosted Pit delivery remains pending")
        db.execute("INSERT INTO seen VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(source, path) DO UPDATE SET session=excluded.session,size=excluded.size,mtime_ns=excluded.mtime_ns,rendered_hash=excluded.rendered_hash,entry_id=excluded.entry_id", (source, metadata["path"], session, metadata["size"], metadata["mtime_ns"], metadata["rendered_hash"], receipt["id"]))
        _save_coverage(db, source, session, metadata["coverage"])
        db.execute("DELETE FROM pending WHERE source=? AND session=?", (source, session))
        db.commit()


def harvest_file(path, *, source, db, client, summary):
    stat = path.stat()
    old = db.execute("SELECT session,size,mtime_ns,rendered_hash FROM seen WHERE source=? AND path=?", (source, str(path))).fetchone()
    if old and (old[1], old[2]) == (stat.st_size, stat.st_mtime_ns):
        return "unchanged"
    metadata = session_metadata(path)
    if metadata is None:
        unresolved = "unresolved:" + hashlib.sha256(str(path).encode()).hexdigest()
        _save_coverage(db, source, unresolved, {"outcome": "missing_session_identity", "path": str(path)})
        db.commit()
        return "unsupported"
    session, started = metadata
    old = db.execute("SELECT size,mtime_ns,rendered_hash FROM seen WHERE source=? AND path=?", (source, str(path))).fetchone()
    try:
        with path.open("rb") as stream:
            rows = CompleteLines(stream)
            rendered, coverage = render_lines(rows, session)
            coverage["partial_trailing_record_omitted"] = rows.partial
    except ValueError as exc:
        if "No supported visible text messages" not in str(exc):
            raise
        _save_coverage(db, source, session, {"outcome": "no_supported_visible_text", "path": str(path)})
        db.commit()
        return "empty"
    summary["messages"] = summary.get("messages", 0) + coverage["messages"]
    summary["partial_trailing_files"] = summary.get("partial_trailing_files", 0) + int(coverage["partial_trailing_record_omitted"])
    for group in ("unsupported", "excluded_record_types"):
        current = summary.setdefault(group, {})
        for key, count in coverage[group].items():
            current[key] = current.get(key, 0) + count
    rendered_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    if old and old[2] == rendered_hash:
        db.execute("UPDATE seen SET session=?,size=?,mtime_ns=? WHERE source=? AND path=?", (session, stat.st_size, stat.st_mtime_ns, source, str(path)))
        _save_coverage(db, source, session, coverage)
        db.commit()
        return "unchanged"
    start = f"Session start: {started}\n" if isinstance(started, str) else ""
    content = f"Source ID: {source}\nSession UUID: {session}\n{start}\n{rendered}"
    queue_delivery(db, source, session, content, {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "rendered_hash": rendered_hash, "coverage": coverage})
    drain_pending(db, source, client)
    return "appended"


def _remote_script(target, manifest):
    renderer = Path(__file__).with_name("transcripts.py").read_text()
    return f'''import hashlib,json,pathlib,sys
exec({renderer!r},globals())
known={manifest!r}
class CompleteLines:
 def __init__(self,stream): self.stream=stream; self.partial=False
 def __iter__(self):
  for row in self.stream:
   if not row.endswith(b"\\n"): self.partial=True; return
   yield row
home=pathlib.Path.home()/".codex"
for folder in (home/"sessions",home/"archived_sessions"):
 for path in sorted(folder.rglob("*.jsonl")) if folder.exists() else ():
  try:
   stat=path.stat(); prior=known.get(str(path))
   if prior==[stat.st_size,stat.st_mtime_ns]:
    print(json.dumps({{"unchanged":True,"path":str(path),"size":stat.st_size,"mtime_ns":stat.st_mtime_ns}})); continue
   session=None; started=None
   with path.open("rb") as f:
    for raw in f:
     try:
      record=json.loads(raw)
      if record.get("type")=="session_meta":
       payload=record.get("payload",{{}}); session=payload.get("id") or payload.get("session_id"); started=payload.get("timestamp") or payload.get("created_at"); break
     except Exception: pass
   if not session:
    unresolved="unresolved:"+hashlib.sha256(str(path).encode()).hexdigest()
    print(json.dumps({{"outcome":"unsupported","session":unresolved,"path":str(path)}})); continue
   with path.open("rb") as f:
    rows=CompleteLines(f); content,coverage=render_lines(rows,session); coverage["partial_trailing_record_omitted"]=rows.partial
   print(json.dumps({{"path":str(path),"session":session,"size":stat.st_size,"mtime_ns":stat.st_mtime_ns,"started":started,"content":content,"rendered_hash":hashlib.sha256(content.encode()).hexdigest(),"coverage":coverage}},ensure_ascii=False))
  except ValueError as exc:
   outcome="empty" if "No supported visible text messages" in str(exc) else "error"
   unresolved="unresolved:"+hashlib.sha256(str(path).encode()).hexdigest()
   print(json.dumps({{"outcome":outcome,"session":session or unresolved,"error":type(exc).__name__,"path":str(path)}}))
  except Exception as exc:
   print(json.dumps({{"outcome":"error","error":type(exc).__name__,"path":str(path)}}))
'''


def remote_snapshots(target, manifest, idle_timeout=120):
    script = _remote_script(target, manifest)
    process = subprocess.Popen(["coder", "ssh", "--disable-autostart", "--wait=no", target, "--", "python3", "-u", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    pending = b""
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(script.encode("utf-8"))
        process.stdin.close()
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            if not selector.select(idle_timeout):
                raise TimeoutError("Remote history scan made no progress")
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                if pending:
                    raise ValueError("Remote history scan ended with an incomplete record")
                status = process.wait(timeout=5)
                if status:
                    raise RuntimeError("Remote history scan failed")
                return
            pending += chunk
            while b"\n" in pending:
                raw_line, pending = pending.split(b"\n", 1)
                if raw_line:
                    yield json.loads(raw_line.decode("utf-8"))
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        for pipe in (process.stdin, process.stdout):
            if pipe is not None and not pipe.closed:
                pipe.close()


def _note(totals, source, outcome, amount=1):
    totals[outcome] = totals.get(outcome, 0) + amount
    by_source = totals.setdefault("sources", {}).setdefault(source, {})
    by_source[outcome] = by_source.get(outcome, 0) + amount


def run_once(args, client=None):
    own_client = client is None
    if own_client:
        client = Client(timeout=args.request_timeout)
        client.start()
    db = checkpoint(Path(args.checkpoint).expanduser())
    totals = {}
    try:
        invalidate_on_parser_change(db)
        sources = [(args.source_id or "local", Path(args.codex_home).expanduser())] + [(target, None) for target in args.coder_target]
        for source, home in sources:
            try:
                source_summary = totals.setdefault("sources", {}).setdefault(source, {})
                source_summary.setdefault("files_seen", 0)
                coverage_summary = source_summary.setdefault("coverage", {})
                pending_count = db.execute("SELECT count(*) FROM pending WHERE source=?", (source,)).fetchone()[0]
                if pending_count:
                    drain_pending(db, source, client)
                    _note(totals, source, "recovered_pending", pending_count)
                if home is not None:
                    if not home.exists():
                        _note(totals, source, "source_errors")
                        continue
                    for path in session_files(home):
                        source_summary["files_seen"] += 1
                        try:
                            _note(totals, source, harvest_file(path, source=source, db=db, client=client, summary=coverage_summary))
                        except DeliveryFailure:
                            _note(totals, source, "delivery_errors")
                            break
                        except Exception:
                            _note(totals, source, "transcript_errors")
                else:
                    manifest = {row[0]: [row[1], row[2]] for row in db.execute("SELECT path,size,mtime_ns FROM seen WHERE source=?", (source,))}
                    for item in remote_snapshots(source, manifest):
                        source_summary["files_seen"] += 1
                        if item.get("unchanged"):
                            db.execute("UPDATE seen SET size=?,mtime_ns=? WHERE source=? AND path=?", (item["size"], item["mtime_ns"], source, item["path"]))
                            db.commit()
                            _note(totals, source, "unchanged")
                            continue
                        if item.get("outcome"):
                            if item.get("session"):
                                _save_coverage(db, source, item["session"], {"outcome": item["outcome"], "path": item.get("path")})
                                db.commit()
                            _note(totals, source, item["outcome"] if item["outcome"] in ("empty", "unsupported") else "transcript_errors")
                            continue
                        old = db.execute("SELECT rendered_hash FROM seen WHERE source=? AND path=?", (source, item["path"])).fetchone()
                        coverage = item["coverage"]
                        coverage_summary["messages"] = coverage_summary.get("messages", 0) + coverage["messages"]
                        for group in ("unsupported", "excluded_record_types"):
                            agg = coverage_summary.setdefault(group, {})
                            for key, count in coverage[group].items():
                                agg[key] = agg.get(key, 0) + count
                        if old and old[0] == item["rendered_hash"]:
                            db.execute("UPDATE seen SET session=?,size=?,mtime_ns=? WHERE source=? AND path=?", (item["session"], item["size"], item["mtime_ns"], source, item["path"]))
                            _save_coverage(db, source, item["session"], coverage)
                            db.commit()
                            _note(totals, source, "unchanged")
                            continue
                        start = f"Session start: {item['started']}\n" if isinstance(item.get("started"), str) else ""
                        content = f"Source ID: {source}\nSession UUID: {item['session']}\n{start}\n{item['content']}"
                        queue_delivery(db, source, item["session"], content, {"path": item["path"], "size": item["size"], "mtime_ns": item["mtime_ns"], "rendered_hash": item["rendered_hash"], "coverage": coverage})
                        drain_pending(db, source, client)
                        _note(totals, source, "appended")
            except DeliveryFailure:
                _note(totals, source, "delivery_errors")
            except Exception:
                _note(totals, source, "source_errors")
    finally:
        db.close()
        if own_client:
            client.close()
    return totals


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", default="~/.codex")
    parser.add_argument("--source-id", default=None, help="stable local source ID (default: local)")
    parser.add_argument("--checkpoint", default="~/.local/state/the-pit/harvest.sqlite3")
    parser.add_argument("--coder-target", action="append", default=[], help="configured target, such as personal.stock")
    parser.add_argument("--request-timeout", type=float, default=30)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=300)
    args = parser.parse_args(argv)
    while True:
        try:
            totals = run_once(args, client=client)
        except Exception:
            print(json.dumps({"source_errors": 1, "error": "collector unavailable"}), flush=True)
            return 1
        print(json.dumps(totals, sort_keys=True), flush=True)
        if args.once:
            return int(bool(totals.get("source_errors") or totals.get("transcript_errors") or totals.get("delivery_errors")))
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
