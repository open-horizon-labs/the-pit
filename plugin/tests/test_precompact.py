import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "hooks/precompact.py"
spec = importlib.util.spec_from_file_location("precompact", SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
THREAD = "11111111-1111-4111-8111-111111111111"


class HookTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.exports = self.root / "exports"
        self.source = self.root / "rollout.jsonl"
        self.secret_text = "  héllo\r\nprivate conversation  "
        records = [{"type": "session_meta", "payload": {"id": THREAD}},
                   {"type": "event_msg", "payload": {"type": "item_completed", "item": {
                       "type": "UserMessage", "id": "u1", "content": [{"type": "text", "text": self.secret_text}]}}}]
        self.source.write_bytes(b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in records))
        self.event = {"hook_event_name": "PreCompact", "trigger": "auto", "session_id": THREAD,
                      "transcript_path": str(self.source), "cwd": "/any/local/project"}
        self.remember = patch.object(hook, "remember").start()
        self.addCleanup(patch.stopall)

    def test_snapshot_is_private_and_saved_before_transport(self):
        def deliver(args, **kwargs):
            output = Path(args[-1])
            self.assertEqual(output.read_bytes(), ("User:\n" + self.secret_text + "\n").encode())
            receipt = json.loads(output.with_suffix(".receipt.json").read_text())
            self.assertEqual(receipt["status"], "delivery_unknown")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(kwargs["timeout"], 45)
            return subprocess.CompletedProcess(args, 0, json.dumps({"id": receipt["sha256"],
                "verified": True, "uploaded": True, "inserted": True, "received_at": "first"}), "")
        with patch.object(hook.subprocess, "run", side_effect=deliver):
            self.assertEqual(hook.run(self.event, self.exports), {"continue": True})
        saved = json.loads(next(self.exports.glob("*.receipt.json")).read_text())
        self.assertEqual(saved["status"], "saved_in_pit")
        self.remember.assert_called_once()
        self.assertEqual(self.remember.call_args.args[0], THREAD)
        self.assertEqual(self.remember.call_args.kwargs["capture"]["end_char"], len("User:\n" + self.secret_text + "\n"))

    def test_unknown_upload_keeps_snapshot_and_does_not_retry_or_leak(self):
        for response in [subprocess.CompletedProcess([], 1, "", self.secret_text),
                         subprocess.TimeoutExpired("client", 45)]:
            with patch.object(hook.subprocess, "run", side_effect=response if isinstance(response, Exception) else None,
                              return_value=response) as send:
                result = hook.run(self.event, self.exports)
            self.assertTrue(result["continue"])
            self.assertNotIn(self.secret_text, json.dumps(result))
            self.assertEqual(send.call_count, 1)
            self.assertEqual(json.loads(list(self.exports.glob("*.receipt.json"))[-1].read_text())["status"], "delivery_unknown")
        self.assertEqual(len(list(self.exports.glob("*.txt"))), 2)
        self.remember.assert_not_called()

    def test_identity_and_format_fail_before_any_upload(self):
        invalid = [{**self.event, "session_id": "22222222-2222-4222-8222-222222222222"},
                   {**self.event, "hook_event_name": "Stop"},
                   {**self.event, "transcript_path": "relative.jsonl"},
                   {**self.event, "session_id": "invalid"},
                   {**self.event, "trigger": "unknown"}]
        with patch.object(hook.subprocess, "run") as send:
            for event in invalid:
                with self.assertRaises((ValueError, KeyError)):
                    hook.run(event, self.exports)
            self.source.write_text('{"type":"unknown_format"}\n')
            with self.assertRaises(ValueError):
                hook.run(self.event, self.exports)
        send.assert_not_called()
        self.assertFalse(self.exports.exists())

    def test_null_path_uses_exact_identity_and_manual_trigger(self):
        event = {**self.event, "transcript_path": None, "trigger": "manual"}
        with patch.object(hook, "locate_rollout", return_value=self.source) as locate, \
             patch.object(hook.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "")):
            self.assertTrue(hook.run(event, self.exports)["continue"])
        self.assertEqual(locate.call_args.args[1], THREAD)

    def test_stdin_failure_is_nonblocking_and_does_not_echo_input(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"private": self.secret_text}),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["continue"])
        self.assertNotIn(self.secret_text, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
