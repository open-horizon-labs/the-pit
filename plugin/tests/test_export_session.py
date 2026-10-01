import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts/export_session.py"
spec = importlib.util.spec_from_file_location("export_session", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
THREAD = "11111111-1111-4111-8111-111111111111"


def snapshot(*items):
    records = [{"type": "session_meta", "payload": {"id": THREAD}}]
    records.extend(items)
    return b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in records)


def message(identity, text, assistant=False):
    item = {"id": identity, "type": "AgentMessage" if assistant else "UserMessage",
            "content": [{"type": "Text" if assistant else "text", "text": text}]}
    if assistant:
        item["phase"] = "final_answer"
    return {"type": "event_msg", "payload": {"type": "item_completed", "item": item}}


class ExportTests(unittest.TestCase):
    def test_preserves_text_order_and_ignores_internal_copies(self):
        first = message("u1", "  čuvaj\ntext  ")
        raw = snapshot(first,
                       {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "copy"}},
                       {"type": "compacted", "payload": {"message": "summary, not transcript"}},
                       message("a1", "Reply", True), first,
                       {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "Reasoning", "raw_content": "internal"}}})
        result, receipt = exporter.render_snapshot(raw, THREAD)
        self.assertEqual(result.decode(), "User:\n  čuvaj\ntext  \n\nAssistant:\nReply\n")
        self.assertEqual(receipt["messages"], 2)
        self.assertEqual(receipt["bytes"], len(result))
        self.assertEqual(exporter.render_snapshot(raw, THREAD)[0], result)

    def test_partial_last_record_is_reported(self):
        result, receipt = exporter.render_snapshot(snapshot(message("1", "done")) + b'{"payload":', THREAD)
        self.assertTrue(receipt["partial_trailing_record_omitted"])
        self.assertIn(b"done", result)

    def test_corrupt_complete_record_fails(self):
        with self.assertRaises(ValueError):
            exporter.render_snapshot(snapshot(message("1", "done")) + b"broken\n", THREAD)

    def test_wrong_session_fails(self):
        with self.assertRaises(ValueError):
            exporter.render_snapshot(snapshot(message("1", "done")), "another-thread")

    def test_conflicting_duplicate_fails(self):
        with self.assertRaises(ValueError):
            exporter.render_snapshot(snapshot(message("1", "old"), message("1", "new")), THREAD)

    def test_nontext_or_unrecognized_phase_fails(self):
        for item in [message("1", "x"), message("2", "x", True)]:
            body = item["payload"]["item"]
            if body["type"] == "UserMessage":
                body["content"].append({"type": "image", "url": "unused"})
            else:
                body["phase"] = "analysis"
            with self.assertRaises(ValueError):
                exporter.render_snapshot(snapshot(item), THREAD)

    def test_cli_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "session.jsonl"
            dest = Path(folder) / "export.txt"
            source.write_bytes(snapshot(message("u1", "hello"), message("a1", "world", True)))
            cmd = [sys.executable, str(SCRIPT), "--thread-id", THREAD, "--rollout", str(source)]
            check = subprocess.run(cmd + ["--check"], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertFalse(dest.exists())
            saved = subprocess.run(cmd + ["--output", str(dest)], capture_output=True, text=True)
            self.assertEqual(saved.returncode, 0, saved.stderr)
            self.assertFalse(json.loads(saved.stdout)["uploaded"])
            self.assertEqual(dest.read_text(), "User:\nhello\n\nAssistant:\nworld\n")
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            repeated = subprocess.run(cmd + ["--output", str(dest)], capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)

    def test_discovery_requires_unique_matching_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                exporter.locate_rollout(root, THREAD)
            for name in ("sessions", "archived_sessions"):
                target = root / name / f"rollout-example-{THREAD}.jsonl"
                target.parent.mkdir()
                target.touch()
                if name == "sessions":
                    self.assertEqual(exporter.locate_rollout(root, THREAD), target)
            with self.assertRaises(ValueError):
                exporter.locate_rollout(root, THREAD)


if __name__ == "__main__":
    unittest.main()
