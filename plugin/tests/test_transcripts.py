import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts"))
from transcripts import render_lines, render_snapshot


THREAD = "01234567-89ab-cdef-0123-456789abcdef"


def line(record):
    return json.dumps(record, separators=(",", ":")).encode()


def session_meta(thread=THREAD):
    return {"type": "session_meta", "payload": {"id": thread}}


def event_message(kind, identity, text, phase=None, timestamp=None):
    item = {"type": kind, "id": identity, "content": [{"type": "text", "text": text}]}
    if phase is not None:
        item["phase"] = phase
    record = {"type": "event_msg", "payload": {"type": "item_completed", "item": item}}
    if timestamp is not None:
        record["timestamp"] = timestamp
    return record


def response_message(role, identity, text, phase=None, timestamp=None):
    payload = {"type": "message", "role": role, "id": identity,
               "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}]}
    if phase is not None:
        payload["phase"] = phase
    record = {"type": "response_item", "payload": payload}
    if timestamp is not None:
        record["timestamp"] = timestamp
    return record


class TranscriptTests(unittest.TestCase):
    def render(self, records):
        return render_snapshot(b"\n".join(map(line, records)) + b"\n", THREAD)

    def test_stable_ids_deduplicate_event_and_response_representations(self):
        text, coverage = self.render([session_meta(), event_message("UserMessage", "m1", "hello"),
                                      response_message("user", "m1", "hello"),
                                      event_message("AgentMessage", "m2", "world", "final_answer"),
                                      response_message("assistant", "m2", "world", "final_answer")])
        self.assertEqual(text, "User:\nhello\n\nAssistant:\nworld\n")
        self.assertEqual(coverage["messages"], 2)
        self.assertEqual(coverage["session_id"], THREAD)

    def test_default_rendering_keeps_legacy_bytes_when_records_have_timestamps(self):
        text, _ = self.render([session_meta(), event_message("UserMessage", "m1", "hello", timestamp="2026-10-04T14:00:00Z")])
        self.assertEqual(text, "User:\nhello\n")

    def test_optional_times_pair_representations_and_choose_earliest_valid_instant(self):
        rows = [session_meta(),
                event_message("UserMessage", "m1", "hello", timestamp="2026-10-04T10:03:00-04:00"),
                response_message("user", "m1", "hello", timestamp="2026-10-04T14:02:00Z")]
        text, coverage = render_lines([line(row) for row in rows], THREAD, include_record_times=True)
        self.assertEqual(text, "Recorded at: 2026-10-04T14:02:00Z\nUser:\nhello\n")
        self.assertEqual(coverage["messages"], 1)
        self.assertEqual(coverage["record_time_coverage"], {
            "source_records_with_valid_timestamp": 2,
            "source_records_missing_timestamp": 0,
            "source_records_with_invalid_timestamp": 0,
            "rendered_messages_with_timestamp": 1,
        })

    def test_optional_times_do_not_merge_repeated_text_with_distinct_ids(self):
        rows = [session_meta(),
                event_message("UserMessage", "m1", "repeat", timestamp="2026-10-04T14:00:00Z"),
                event_message("UserMessage", "m2", "repeat", timestamp="2026-10-04T14:01:00Z")]
        text, coverage = render_lines([line(row) for row in rows], THREAD, include_record_times=True)
        self.assertEqual(text, "Recorded at: 2026-10-04T14:00:00Z\nUser:\nrepeat\n\nRecorded at: 2026-10-04T14:01:00Z\nUser:\nrepeat\n")
        self.assertEqual(coverage["messages"], 2)

    def test_optional_times_omit_missing_and_invalid_values_with_coverage(self):
        rows = [session_meta(), event_message("UserMessage", "m1", "missing"),
                event_message("UserMessage", "m2", "invalid", timestamp="2026-10-04T14:00:00")]
        text, coverage = render_lines([line(row) for row in rows], THREAD, include_record_times=True)
        self.assertEqual(text, "User:\nmissing\n\nUser:\ninvalid\n")
        self.assertEqual(coverage["record_time_coverage"], {
            "source_records_with_valid_timestamp": 0,
            "source_records_missing_timestamp": 1,
            "source_records_with_invalid_timestamp": 1,
            "rendered_messages_with_timestamp": 0,
        })

    def test_legacy_missing_ids_and_phase_pair_once(self):
        records = [session_meta(), event_message("UserMessage", None, "hello"), response_message("user", None, "hello"),
                   event_message("AgentMessage", None, "answer"), response_message("assistant", None, "answer")]
        for row in records[1:]:
            target = row["payload"].get("item", row["payload"])
            target.pop("id", None)
            target.pop("phase", None)
        text, coverage = self.render(records)
        self.assertEqual(text, "User:\nhello\n\nAssistant:\nanswer\n")
        self.assertEqual(coverage["messages"], 2)

    def test_mixed_id_fallback_pairs_one_to_one_within_same_text_run(self):
        event = event_message("UserMessage", "known", "repeat")
        second_event = event_message("UserMessage", "second", "repeat")
        response = response_message("user", None, "repeat")
        response["payload"].pop("id")
        second_response = response_message("user", None, "repeat")
        second_response["payload"].pop("id")
        text, coverage = self.render([session_meta(), event, second_event, response, second_response])
        self.assertEqual(text, "User:\nrepeat\n\nUser:\nrepeat\n")
        self.assertEqual(coverage["messages"], 2)

    def test_same_text_in_distinct_stable_turns_is_never_globally_paired(self):
        records = [session_meta(), response_message("user", "user-a", "go"),
                   response_message("assistant", "assistant-a", "okay"), event_message("UserMessage", "user-b", "go")]
        text, coverage = self.render(records)
        self.assertEqual(text, "User:\ngo\n\nAssistant:\nokay\n\nUser:\ngo\n")
        self.assertEqual(coverage["messages"], 3)

    def test_adjacent_same_phrase_with_distinct_ids_remains_two_turns(self):
        text, coverage = self.render([session_meta(), event_message("UserMessage", "one", "repeat"), event_message("UserMessage", "two", "repeat")])
        self.assertEqual(text, "User:\nrepeat\n\nUser:\nrepeat\n")
        self.assertEqual(coverage["messages"], 2)

    def test_missing_id_pair_marks_stable_id_before_later_duplicate(self):
        legacy = response_message("user", None, "hello")
        legacy["payload"].pop("id")
        text, coverage = self.render([session_meta(), legacy, event_message("UserMessage", "known", "hello"), event_message("UserMessage", "known", "hello")])
        self.assertEqual(text, "User:\nhello\n")
        self.assertEqual(coverage["messages"], 1)

    def test_excludes_developer_reasoning_tools_and_internal_assistant_phases(self):
        records = [session_meta(), response_message("developer", "d1", "secret"),
                   {"type": "response_item", "payload": {"type": "reasoning", "summary": "hidden"}},
                   {"type": "response_item", "payload": {"type": "function_call", "name": "x"}},
                   response_message("assistant", "a1", "private", "analysis"), response_message("user", "u1", "visible")]
        text, coverage = self.render(records)
        self.assertEqual(text, "User:\nvisible\n")
        self.assertEqual(coverage["unsupported"]["unsupported_response_assistant_phase"], 1)

    def test_incomplete_trailing_record_is_omitted(self):
        raw = b"\n".join(map(line, [session_meta(), event_message("UserMessage", "m1", "ok")])) + b"\n{partial"
        text, coverage = render_snapshot(raw, THREAD)
        self.assertEqual(text, "User:\nok\n")
        self.assertTrue(coverage["partial_trailing_record_omitted"])

    def test_first_identity_must_match_requested_thread(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.render([session_meta("fedcba98-7654-3210-fedc-ba9876543210"), event_message("UserMessage", "m1", "hi")])

    def test_rollout_id_overrides_subagent_session_id(self):
        meta = {"type": "session_meta", "payload": {"id": THREAD, "session_id": "parent", "parent_thread_id": "parent"}}
        text, coverage = self.render([meta, event_message("UserMessage", "m1", "hello")])
        self.assertEqual(text, "User:\nhello\n")
        self.assertEqual(coverage["session_id"], THREAD)

    def test_fork_parent_metadata_requires_explicit_link(self):
        parent = "fedcba98-7654-3210-fedc-ba9876543210"
        linked = session_meta()
        linked["payload"].update({"forked_from_id": parent, "parent_thread_id": parent})
        text, coverage = self.render([linked, {"type": "session_meta", "payload": {"id": parent}}, event_message("UserMessage", "m1", "fork")])
        self.assertEqual(text, "User:\nfork\n")
        self.assertEqual(coverage["inherited_sessions"], [parent])
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.render([session_meta(), {"type": "session_meta", "payload": {"id": parent}}])

    def test_optional_times_render_for_explicitly_inherited_fork_records(self):
        parent = "fedcba98-7654-3210-fedc-ba9876543210"
        rows = [
            {"type": "session_meta", "payload": {"id": THREAD, "forked_from_id": parent}},
            {"type": "session_meta", "payload": {"id": parent}},
            event_message("UserMessage", "fork-message", "fork", timestamp="2026-10-04T14:00:00Z"),
        ]
        text, coverage = render_lines([line(row) for row in rows], THREAD, include_record_times=True)
        self.assertEqual(text, "Recorded at: 2026-10-04T14:00:00Z\nUser:\nfork\n")
        self.assertEqual(coverage["inherited_sessions"], [parent])

    def test_mixed_text_and_nontext_keeps_text_and_reports_omissions(self):
        record = response_message("user", "i1", "unused")
        record["payload"]["content"] = [{"type": "input_text", "text": "visible"}, {"type": "input_image", "image_url": "omitted"}]
        text, coverage = self.render([session_meta(), record])
        self.assertEqual(text, "User:\nvisible\n")
        self.assertEqual(coverage["unsupported"]["response_non_text_parts_excluded"], 1)

    def test_image_only_message_is_omitted(self):
        record = response_message("user", "i1", "unused")
        record["payload"]["content"] = [{"type": "input_image", "image_url": "omitted"}]
        with self.assertRaisesRegex(ValueError, "No supported visible text"):
            self.render([session_meta(), record])

    def test_conflicting_duplicate_identity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "different text"):
            self.render([session_meta(), event_message("UserMessage", "same", "one"), response_message("user", "same", "two")])

    def test_invalid_complete_record_fails_and_partial_tail_is_tolerated(self):
        with self.assertRaisesRegex(ValueError, "Invalid complete JSON"):
            render_snapshot(line(session_meta()) + b"\nnot-json\n", THREAD)
        base = line(session_meta()) + b"\n" + line(event_message("UserMessage", "m1", "ok")) + b"\n"
        text, coverage = render_snapshot(base + b"{truncated", THREAD)
        self.assertEqual(text, "User:\nok\n")
        self.assertTrue(coverage["partial_trailing_record_omitted"])


if __name__ == "__main__":
    unittest.main()
