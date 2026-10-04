"""Export completed visible message events and optionally append them to The Pit."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def render_snapshot(raw, thread_id):
    # A live writer may have left a partial last record at our byte boundary.
    trailing = bool(raw and not raw.endswith(b"\n"))
    if trailing:
        raw = raw.rsplit(b"\n", 1)[0] if b"\n" in raw else b""
    messages = []
    seen = {}
    session_id = None
    for number, line in enumerate(raw.splitlines(), 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Invalid complete JSON record at line {number}") from exc
        payload = record.get("payload", {})
        if record.get("type") == "session_meta":
            found = payload.get("id") or payload.get("session_id")
            if found != thread_id:
                raise ValueError("Session identity does not match the requested thread")
            session_id = found
        if record.get("type") != "event_msg" or payload.get("type") != "item_completed":
            continue
        item = payload.get("item", {})
        kind = item.get("type")
        if kind not in ("UserMessage", "AgentMessage"):
            continue
        if kind == "AgentMessage" and item.get("phase") not in ("commentary", "final_answer"):
            raise ValueError("Unsupported assistant message phase; export stopped")
        identity = item.get("id")
        if not isinstance(identity, str) or not identity:
            raise ValueError("Message has no stable event identity")
        parts = item.get("content")
        if not isinstance(parts, list) or not parts:
            raise ValueError("Unsupported message content; export stopped")
        texts = []
        for part in parts:
            if not isinstance(part, dict) or part.get("type") not in ("text", "Text"):
                raise ValueError("Non-text message content found; this exporter supports text only")
            if not isinstance(part.get("text"), str):
                raise ValueError("Message text is missing")
            texts.append(part["text"])
        role = "User" if kind == "UserMessage" else "Assistant"
        message = (role, "\n".join(texts))
        if identity in seen:
            if seen[identity] != message:
                raise ValueError("Repeated message identity has different text; export stopped")
            continue
        seen[identity] = message
        messages.append(message)
    if session_id is None or not messages:
        raise ValueError("No supported local session with completed message events found")
    content = "\n\n".join(f"{role}:\n{text}" for role, text in messages) + "\n"
    encoded = content.encode("utf-8")
    return encoded, {
        "messages": len(messages),
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "partial_trailing_record_omitted": trailing,
        "coverage": "completed user and assistant text; excludes tools, attachments and internal records",
    }


def locate_rollout(root, thread_id):
    # Validate before using identity in a glob; never fall back to another chat.
    import uuid
    try:
        uuid.UUID(thread_id)
    except ValueError as exc:
        raise ValueError("Thread identity must be a UUID") from exc
    paths = []
    for folder in (root / "sessions", root / "archived_sessions"):
        paths.extend(folder.rglob(f"rollout-*-{thread_id}.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"Expected one record for this thread; found {len(paths)}")
    return paths[0]


def save_snapshot(content, destination):
    if not destination.is_absolute():
        raise ValueError("Output must be an absolute path")
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread-id", default=os.environ.get("CODEX_THREAD_ID"))
    parser.add_argument("--rollout", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate and report counts without saving text")
    mode.add_argument("--output", type=Path)
    mode.add_argument("--upload", action="store_true", help="save a private snapshot and append to configured Pit")
    args = parser.parse_args()
    if not args.thread_id:
        parser.error("Current thread identity unavailable; provide --thread-id explicitly")
    try:
        root = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
        path = args.rollout or locate_rollout(root, args.thread_id)
        with path.open("rb") as source:
            raw = source.read(os.fstat(source.fileno()).st_size)
        content, receipt = render_snapshot(raw, args.thread_id)
        if args.upload:
            folder = Path.home() / ".local/share/the-pit/exports"
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(folder, 0o700)
            import uuid
            args.output = folder / f"{args.thread_id}-{uuid.uuid4()}.txt"
        if args.output:
            save_snapshot(content, args.output)
            receipt["output"] = str(args.output)
        receipt["status"] = "validated" if args.check else "local_export_only"
        receipt["uploaded"] = False
        if args.upload:
            from pit_support import PitError, DeliveryUnknown
            from hosted_client import Client
            try:
                with Client() as client:
                    receipt.update(client.append(content.decode("utf-8")))
                receipt["status"] = "saved_in_pit"
            except (PitError, OSError, ValueError, KeyError) as exc:
                receipt["status"] = "delivery_unknown" if isinstance(exc, DeliveryUnknown) else "upload_failed"
                receipt["uploaded"] = None if isinstance(exc, DeliveryUnknown) else False
                receipt["error"] = str(exc) if isinstance(exc, PitError) else "Connection unavailable"
                print(json.dumps(receipt, indent=2))
                return 1
        print(json.dumps(receipt, indent=2))
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
