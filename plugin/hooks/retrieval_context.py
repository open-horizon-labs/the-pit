"""Keep only validated entry/range pointers for the exact local host session."""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts"
sys.path.insert(0, str(SCRIPTS))
from pit_support import save_config

STATE = Path.home() / ".local/share/the-pit/retrieval"
TOOL_NAME = re.compile(r"^mcp__pit__pit_(search|read_range)$")


def session_key(identity):
    return str(uuid.UUID(identity))


def valid_anchor(row):
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not re.fullmatch(r"[a-f0-9]{64}", row["id"]):
        raise ValueError("Invalid anchor")
    start, end = row.get("start_char"), row.get("end_char")
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= 2147483647 or end - start > 20000:
        raise ValueError("Invalid anchor range")
    return {"id": row["id"], "start_char": start, "end_char": end}


def load_state(identity, root=STATE):
    identity = session_key(identity)
    path = root / (identity + ".json")
    if not path.exists():
        return {"session_id": identity, "anchors": []}
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("Unsafe state file")
    data = json.loads(path.read_text())
    if data.get("session_id") != identity:
        raise ValueError("Wrong session")
    anchors = [valid_anchor(a) for a in data.get("anchors", [])][-8:]
    result = {"session_id": identity, "anchors": anchors}
    if data.get("capture") is not None:
        result["capture"] = valid_anchor(data["capture"])
    return result


def remember(identity, anchors=(), capture=None, root=STATE):
    identity = session_key(identity)
    anchors = [valid_anchor(a) for a in anchors]
    capture = valid_anchor(capture) if capture is not None else None
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    fd = os.open(root / (identity + ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load_state(identity, root)
        for anchor in anchors:
            data["anchors"] = [a for a in data["anchors"] if a != anchor] + [anchor]
        data["anchors"] = data["anchors"][-8:]
        if capture is not None:
            data["capture"] = capture
        save_config(data, root / (identity + ".json"))


def reader_rows(response):
    if isinstance(response, str):
        response = json.loads(response)
    if not isinstance(response, dict) or response.get("isError"):
        return []
    structured = response.get("structuredContent")
    if isinstance(structured, dict):
        return structured.get("entries", [])
    # Native MCP results can contain just JSON text content blocks.
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            data = json.loads(block["text"])
            if isinstance(data, dict) and isinstance(data.get("entries"), list):
                return data["entries"]
    return []


def run(event, root=STATE):
    if not isinstance(event, dict):
        raise ValueError("Invalid event")
    identity = session_key(event["session_id"])
    name = event.get("hook_event_name")
    if name == "PostToolUse":
        if not TOOL_NAME.fullmatch(event.get("tool_name", "")):
            return {"continue": True}
        rows = reader_rows(event.get("tool_response"))
        if not isinstance(rows, list) or len(rows) > 20:
            raise ValueError("Invalid reader response")
        remember(identity, rows, root=root)
        return {"continue": True}
    if name != "SessionStart" or event.get("source") not in ("startup", "resume", "compact"):
        raise ValueError("Unsupported event")
    context = 'The precompaction conversation is available in The Pit. Trust the compaction summary. Make narrow Pit checks at substantial task starts and decision points; compaction alone does not trigger retrieval. Do not automatically reload earlier conversation text.'
    return {"continue": True, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}


def main():
    try:
        result = run(json.load(sys.stdin))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        result = {"continue": True, "systemMessage": "Pit recovery pointers unavailable; compaction/session can continue. Search remains available."}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
