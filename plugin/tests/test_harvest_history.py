import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts"
sys.path.insert(0, str(SCRIPTS))
import harvest_history as harvest


THREAD = "01234567-89ab-cdef-0123-456789abcdef"


def record(value):
    return json.dumps(value, separators=(",", ":")) + "\n"


class FakePit:
    def __init__(self, failures=0):
        self.failures = failures
        self.entries = []

    def append(self, content):
        self.entries.append(content)
        if self.failures:
            self.failures -= 1
            raise RuntimeError("delivery unknown")
        import hashlib
        return {"id": hashlib.sha256(content.encode()).hexdigest(), "verified": True}


class HarvestHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "sessions" / "session.jsonl"
        self.path.parent.mkdir(parents=True)
        self.write_rollout()
        self.db = harvest.checkpoint(self.root / "state" / "harvest.sqlite3")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def write_rollout(self, text="hello", extra=None):
        records = [
            {"type": "session_meta", "payload": {"id": THREAD, "session_id": "parent-session", "timestamp": "2026-10-01T12:00:00Z"}},
            {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "text", "text": text}, {"type": "image", "url": "omitted"}]}}},
        ]
        if extra:
            records.append(extra)
        self.path.write_text("".join(record(row) for row in records))

    def test_retry_and_exact_content_dedup_use_verified_hosted_receipts(self):
        client = FakePit(failures=1)
        with self.assertRaises(RuntimeError):
            harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={})
        self.assertEqual(self.db.execute("SELECT count(*) FROM seen").fetchone()[0], 0)
        result = harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={})
        self.assertEqual(result, "appended")
        self.assertEqual(client.entries[0], client.entries[1])
        self.assertIn("Session UUID: " + THREAD, client.entries[1])
        self.assertIn("User:\nhello", client.entries[1])
        coverage = json.loads(self.db.execute("SELECT details FROM coverage WHERE source='local' AND session=?", (THREAD,)).fetchone()[0])
        self.assertEqual(coverage["unsupported"]["event_non_text_parts_excluded"], 1)

    def test_unknown_delivery_retries_saved_bytes_before_scanning_changed_or_missing_source(self):
        original = FakePit(failures=1)
        with self.assertRaises(RuntimeError):
            harvest.harvest_file(self.path, source="local", db=self.db, client=original, summary={})
        saved = self.db.execute("SELECT content FROM pending WHERE source='local' AND session=?", (THREAD,)).fetchone()[0]
        self.assertIn("User:\nhello", saved)
        self.path.unlink()
        args = type("Args", (), {"codex_home": str(self.root), "source_id": "local", "checkpoint": str(self.root / "state" / "harvest.sqlite3"), "coder_target": [], "request_timeout": 5})()
        retry = FakePit()
        result = harvest.run_once(args, client=retry)
        self.assertEqual(retry.entries, [saved])
        self.assertEqual(result["recovered_pending"], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM pending").fetchone()[0], 0)

    def test_unchanged_rendered_text_refreshes_stat_checkpoint(self):
        client = FakePit()
        harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={})
        self.write_rollout(extra={"type": "response_item", "payload": {"type": "reasoning", "summary": "hidden"}})
        self.assertEqual(harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={}), "unchanged")
        stat = self.path.stat()
        row = self.db.execute("SELECT size,mtime_ns FROM seen WHERE source='local' AND session=?", (THREAD,)).fetchone()
        self.assertEqual(row, (stat.st_size, stat.st_mtime_ns))

    def test_remote_command_has_configured_coder_target_and_bounded_timeout(self):
        original = harvest.subprocess.Popen
        calls = []
        children = []
        child_code = "import sys,json; compile(sys.stdin.buffer.read(), 'remote.py', 'exec'); print(json.dumps({'session':'one'}),flush=True); import time; time.sleep(.2); print(json.dumps({'session':'two'}),flush=True)"
        def fake_popen(argv, **kwargs):
            calls.append((argv, kwargs))
            child = original([sys.executable, "-u", "-c", child_code], **kwargs)
            children.append(child)
            return child
        harvest.subprocess.Popen = fake_popen
        try:
            rows = harvest.remote_snapshots("personal.stock", {"/remote/session": [1, 2]})
            self.assertEqual(next(rows), {"session": "one"})
            self.assertIsNone(children[0].poll(), "the first result should stream before remote process exit")
            self.assertEqual(next(rows), {"session": "two"})
            with self.assertRaises(StopIteration):
                next(rows)
        finally:
            harvest.subprocess.Popen = original
        argv, kwargs = calls[0]
        self.assertEqual(argv[:5], ["coder", "ssh", "--disable-autostart", "--wait=no", "personal.stock"])
        self.assertEqual(argv[6:9], ["python3", "-u", "-"])
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)

    def test_remote_idle_timeout_kills_stalled_process(self):
        original = harvest.subprocess.Popen
        children = []
        def fake_popen(argv, **kwargs):
            child = original([sys.executable, "-u", "-c", "import sys,time; sys.stdin.buffer.read(); time.sleep(1)"], **kwargs)
            children.append(child)
            return child
        harvest.subprocess.Popen = fake_popen
        try:
            with self.assertRaises(TimeoutError):
                list(harvest.remote_snapshots("personal.stock", {}, idle_timeout=0.05))
        finally:
            harvest.subprocess.Popen = original
        self.assertIsNotNone(children[0].poll())

    def test_renderer_accepts_linked_fork_metadata_and_rejects_unrelated_session(self):
        parent = "fedcba98-7654-3210-fedc-ba9876543210"
        records = [
            {"type": "session_meta", "payload": {"id": THREAD, "forked_from_id": parent, "parent_thread_id": parent}},
            {"type": "session_meta", "payload": {"id": parent}},
            {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "text", "text": "forked"}]}}},
        ]
        rendered, coverage = harvest.render_lines([record(row).encode() for row in records], THREAD)
        self.assertEqual(rendered, "User:\nforked\n")
        self.assertEqual(coverage["inherited_sessions"], [parent])
        with self.assertRaisesRegex(ValueError, "does not match"):
            harvest.render_lines([record(records[0]).encode(), record({"type": "session_meta", "payload": {"id": "unrelated"}}).encode()], THREAD)

    def test_parser_change_invalidates_stat_cache_without_replacing_receipt(self):
        client = FakePit()
        harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={})
        entry_id = self.db.execute("SELECT entry_id FROM seen WHERE source='local' AND session=?", (THREAD,)).fetchone()[0]
        self.db.execute("INSERT INTO metadata VALUES ('renderer_sha256','old') ON CONFLICT(key) DO UPDATE SET value='old'")
        harvest.invalidate_on_parser_change(self.db)
        self.assertEqual(self.db.execute("SELECT mtime_ns FROM seen WHERE source='local' AND session=?", (THREAD,)).fetchone()[0], -1)
        self.assertEqual(harvest.harvest_file(self.path, source="local", db=self.db, client=client, summary={}), "unchanged")
        self.assertEqual(len(client.entries), 1)
        self.assertEqual(self.db.execute("SELECT entry_id FROM seen WHERE source='local' AND session=?", (THREAD,)).fetchone()[0], entry_id)

    def test_checkpoint_migrates_development_file_hash_column(self):
        legacy = self.root / "legacy.sqlite3"
        import sqlite3
        old = sqlite3.connect(legacy)
        old.execute("CREATE TABLE seen (source TEXT NOT NULL, session TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, file_hash TEXT NOT NULL, entry_id TEXT NOT NULL, PRIMARY KEY(source,session))")
        old.execute("INSERT INTO seen VALUES ('local', ?, '/old/rollout.jsonl', 10, 20, 'render-hash', 'pit-entry')", (THREAD,))
        old.commit()
        old.close()
        migrated = harvest.checkpoint(legacy)
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(seen)")}
        self.assertIn("rendered_hash", columns)
        self.assertNotIn("file_hash", columns)
        primary_key = [row[1] for row in sorted((row for row in migrated.execute("PRAGMA table_info(seen)") if row[5]), key=lambda row: row[5])]
        self.assertEqual(primary_key, ["source", "path"])
        self.assertEqual(migrated.execute("SELECT session,entry_id FROM seen WHERE source='local' AND path='/old/rollout.jsonl'").fetchone(), (THREAD, "pit-entry"))
        self.assertIsNone(migrated.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seen_new'").fetchone())
        migrated.close()
        reopened = harvest.checkpoint(legacy)
        self.assertEqual(reopened.execute("SELECT session,entry_id FROM seen WHERE source='local' AND path='/old/rollout.jsonl'").fetchone(), (THREAD, "pit-entry"))
        reopened.close()

    def test_active_and_archived_paths_for_same_session_keep_separate_checkpoints(self):
        home = self.root / "duplicates"
        active = home / "sessions" / "active.jsonl"
        archived = home / "archived_sessions" / "archived.jsonl"
        active.parent.mkdir(parents=True)
        archived.parent.mkdir(parents=True)
        def write(path, text):
            rows = [{"type": "session_meta", "payload": {"id": THREAD}}, {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "text", "text": text}]}}}]
            path.write_text("".join(record(row) for row in rows))
        write(active, "active copy")
        write(archived, "archived copy")
        args = type("Args", (), {"codex_home": str(home), "source_id": "local", "checkpoint": str(self.root / "duplicates.sqlite3"), "coder_target": [], "request_timeout": 5})()
        client = FakePit()
        first = harvest.run_once(args, client=client)
        second = harvest.run_once(args, client=client)
        self.assertEqual(first["appended"], 2)
        self.assertEqual(second["unchanged"], 2)
        self.assertEqual(len(client.entries), 2)
        db = sqlite3.connect(args.checkpoint)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM seen WHERE source='local' AND session=?", (THREAD,)).fetchone()[0], 2)
        finally:
            db.close()

    def test_once_reports_named_empty_source_and_fails_on_operational_errors(self):
        args = type("Args", (), {"codex_home": str(self.root / "empty"), "source_id": "empty-account", "checkpoint": str(self.root / "empty.sqlite3"), "coder_target": [], "request_timeout": 5})()
        result = harvest.run_once(args, client=FakePit())
        self.assertEqual(result["sources"]["empty-account"]["files_seen"], 0)
        with patch.object(harvest, "run_once", return_value={"source_errors": 1}):
            self.assertEqual(harvest.main(["--once"]), 1)
        with patch.object(harvest, "run_once", return_value={"empty": 5, "unsupported": 2}):
            self.assertEqual(harvest.main(["--once"]), 0)

    def test_independent_source_failure_does_not_hide_successful_local_source(self):
        args = type("Args", (), {"codex_home": str(self.root), "source_id": "local", "checkpoint": str(self.root / "other.sqlite3"), "coder_target": ["personal.stock"], "request_timeout": 5})()
        with patch.object(harvest, "remote_snapshots", side_effect=OSError("remote down")):
            result = harvest.run_once(args, client=FakePit())
        self.assertEqual(result["appended"], 1)
        self.assertEqual(result["source_errors"], 1)
        self.assertEqual(result["sources"]["local"]["appended"], 1)
        self.assertEqual(result["sources"]["personal.stock"]["source_errors"], 1)

    def test_sink_failure_stops_retries_for_source_but_later_sources_are_reported(self):
        home = self.root / "many"
        folder = home / "sessions"
        folder.mkdir(parents=True)
        for index in range(100):
            thread = f"00000000-0000-0000-0000-{index:012d}"
            path = folder / f"{thread}.jsonl"
            path.write_text(record({"type": "session_meta", "payload": {"id": thread}}) + record({"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "text", "text": str(index)}]}}}))
        args = type("Args", (), {"codex_home": str(home), "source_id": "local", "checkpoint": str(self.root / "fail.sqlite3"), "coder_target": ["personal.stock"], "request_timeout": 5})()
        client = FakePit(failures=1)
        with patch.object(harvest, "remote_snapshots", return_value=iter(())):
            result = harvest.run_once(args, client=client)
        self.assertEqual(len(client.entries), 1)
        self.assertEqual(result["sources"]["local"]["files_seen"], 1)
        self.assertEqual(result["sources"]["local"]["delivery_errors"], 1)
        self.assertIn("personal.stock", result["sources"])


if __name__ == "__main__":
    unittest.main()
