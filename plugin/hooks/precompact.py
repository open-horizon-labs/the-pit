"""Capture local completed message text before compaction; never block compaction."""

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_session import locate_rollout, render_snapshot, save_snapshot
from pit_client import save_config
from retrieval_context import remember

EXPORTS = Path.home() / ".local/share/the-pit/exports"


def run(event, exports=EXPORTS):
    # Only host-provided event identity selects the conversation. No newest-file fallback.
    if not isinstance(event, dict) or event.get("hook_event_name") != "PreCompact" or event.get("trigger") not in ("manual", "auto"):
        raise ValueError("Unsupported hook event")
    identity = str(uuid.UUID(event["session_id"]))
    supplied = event.get("transcript_path")
    if supplied is None:
        source = locate_rollout(Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser(), identity)
    elif isinstance(supplied, str) and supplied and Path(supplied).is_absolute():
        source = Path(supplied)
    else:
        raise ValueError("Invalid transcript path")
    with source.open("rb") as stream:
        raw = stream.read(os.fstat(stream.fileno()).st_size)
    content, receipt = render_snapshot(raw, identity)
    exports.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(exports, 0o700)
    output = exports / f"{identity}-{uuid.uuid4()}.txt"
    save_snapshot(content, output)
    receipt.update(output=str(output), trigger=event["trigger"], status="delivery_unknown", uploaded=None)
    receipt_path = output.with_suffix(".receipt.json")
    # Record the recoverable file before starting any remote operation.
    save_config(receipt, receipt_path)
    try:
        process = subprocess.run([sys.executable, str(SCRIPTS / "pit_client.py"),
                                  "--request-timeout", "10", "--append-file", str(output)],
                                 capture_output=True, text=True, timeout=45)
        if process.returncode == 0:
            delivered = json.loads(process.stdout)
            if delivered.get("id") != receipt["sha256"] or delivered.get("verified") is not True:
                raise ValueError("Invalid delivery receipt")
            receipt.update(delivered, status="saved_in_pit")
            save_config(receipt, receipt_path)
            try:
                characters = len(content.decode("utf-8"))
                remember(identity, capture={"id": delivered["id"],
                         "start_char": max(0, characters - 1000), "end_char": characters})
            except (OSError, ValueError, TypeError, KeyError):
                return {"continue": True, "systemMessage": "Pit capture verified; recovery pointer could not be saved. The private receipt remains available."}
            return {"continue": True}
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass
    # A nonzero child or timeout is conservative unknown delivery, with no automatic retry.
    return {"continue": True, "systemMessage":
            f"Pit upload is unconfirmed. Snapshot retained at {output}. "
            "Recover with pit_client.py --verify-file using that file; compaction can continue."}


def main():
    try:
        event = json.load(sys.stdin)
        result = run(event)
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        result = {"continue": True, "systemMessage":
                  "Pit automatic export failed: local transcript identity, format, or snapshot storage is unavailable. "
                  "Compaction can continue; no successful upload is claimed."}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
