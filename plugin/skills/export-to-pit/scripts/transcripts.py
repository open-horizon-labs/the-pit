"""Render visible text from supported local Codex rollout transcript records.

This module is intentionally a pure parser: it neither locates sessions nor writes
to The Pit. Upstream rollout formats are versioned in practice, so unknown message
shapes are reported in coverage and omitted.
"""

from __future__ import annotations

import hashlib
import json


_ASSISTANT_PHASES = {"commentary", "final_answer"}


def _message_text(parts, allowed_types):
    if not isinstance(parts, list) or not parts:
        return None, "missing_or_empty_content", False
    texts = []
    omitted = False
    for part in parts:
        if not isinstance(part, dict) or part.get("type") not in allowed_types or not isinstance(part.get("text"), str):
            omitted = True
            continue
        texts.append(part["text"])
    if not texts:
        return None, "unsupported_content_part" if omitted else "missing_text", omitted
    return "\n".join(texts), None, omitted


def render_lines(lines, thread_id: str, *, partial_trailing_record_omitted=False):
    """Render a stream of complete JSONL records for exactly *thread_id*."""

    session_id = None
    linked_sessions = set()
    inherited_sessions = set()
    messages = []
    seen = {}
    run_key = None
    unmatched = {"event": [], "response": []}
    unsupported = {}
    excluded_record_types = {}

    def omit(reason):
        unsupported[reason] = unsupported.get(reason, 0) + 1

    for number, line in enumerate(lines, 1):
        if isinstance(line, str):
            line = line.encode("utf-8")
        if line.endswith(b"\n"):
            line = line[:-1]
        if not line:
            continue
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Invalid complete JSON record at line {number}") from exc
        if not isinstance(record, dict):
            omit("non_object_record")
            continue
        record_type = record.get("type")
        payload = record.get("payload")

        if record_type == "session_meta":
            if not isinstance(payload, dict):
                raise ValueError("Session metadata is malformed")
            found = payload.get("id") or payload.get("session_id")
            if not isinstance(found, str) or not found:
                raise ValueError("Session metadata has no exact session identity")
            if session_id is None:
                if found != thread_id:
                    raise ValueError("Session identity does not match the requested thread")
                session_id = found
            elif found != thread_id:
                if found not in linked_sessions:
                    raise ValueError("Session identity does not match the requested thread")
                inherited_sessions.add(found)
            for link in (payload.get("forked_from_id"), payload.get("parent_thread_id")):
                if isinstance(link, str) and link:
                    linked_sessions.add(link)
            continue

        candidate = None
        if record_type == "event_msg" and isinstance(payload, dict) and payload.get("type") == "item_completed":
            item = payload.get("item")
            if isinstance(item, dict) and item.get("type") in ("UserMessage", "AgentMessage"):
                kind = item["type"]
                if kind == "AgentMessage" and item.get("phase") not in (None, *_ASSISTANT_PHASES):
                    omit("unsupported_event_assistant_phase")
                    continue
                text, reason, omitted = _message_text(item.get("content"), {"text", "Text"})
                if reason:
                    omit("event_" + reason)
                    continue
                if omitted:
                    omit("event_non_text_parts_excluded")
                role = "User" if kind == "UserMessage" else "Assistant"
                candidate = (item.get("id"), role, text, "event")
            elif isinstance(item, dict):
                # Tool, reasoning, and other internal records are intentionally excluded.
                continue
            else:
                omit("malformed_completed_event")
                continue
        elif record_type == "response_item" and isinstance(payload, dict) and payload.get("type") == "message":
            role_value = payload.get("role")
            if role_value not in ("user", "assistant"):
                continue
            if role_value == "assistant" and payload.get("phase") not in (None, *_ASSISTANT_PHASES):
                omit("unsupported_response_assistant_phase")
                continue
            text, reason, omitted = _message_text(payload.get("content"), {"input_text", "output_text"})
            if reason:
                omit("response_" + reason)
                continue
            if omitted:
                omit("response_non_text_parts_excluded")
            candidate = (payload.get("id"), "User" if role_value == "user" else "Assistant", text, "response")
        elif record_type not in ("session_meta", "event_msg", "response_item"):
            excluded_record_types[str(record_type)] = excluded_record_types.get(str(record_type), 0) + 1
            continue
        else:
            # Event and response variants outside the verified text-message forms.
            if record_type == "event_msg" and isinstance(payload, dict) and payload.get("type") == "item_completed":
                omit("unsupported_event_record")
            elif record_type == "response_item" and isinstance(payload, dict) and payload.get("type") not in ("message", "reasoning"):
                continue

        if candidate is None:
            continue
        identity, role, text, representation = candidate
        message = (role, text)
        has_identity = isinstance(identity, str) and bool(identity)
        candidate_key = (role, text)
        if candidate_key != run_key:
            run_key = candidate_key
            unmatched = {"event": [], "response": []}
        if has_identity and identity in seen:
            if seen[identity] != message:
                raise ValueError("Repeated message identity has different text; export stopped")
            continue
        if has_identity:
            seen[identity] = message
        opposite = "response" if representation == "event" else "event"
        duplicate_pair = None
        for index, prior_identity in enumerate(unmatched[opposite]):
            prior_has_identity = isinstance(prior_identity, str) and bool(prior_identity)
            if not (prior_has_identity and has_identity):
                duplicate_pair = index
                break
        if duplicate_pair is None:
            messages.append(message)
            unmatched[representation].append(identity if has_identity else None)
        else:
            unmatched[opposite].pop(duplicate_pair)

    if session_id is None:
        raise ValueError("No matching session metadata found")
    if not messages:
        raise ValueError("No supported visible text messages found")
    content = "\n\n".join(f"{role}:\n{text}" for role, text in messages) + "\n"
    encoded = content.encode("utf-8")
    return content, {
        "session_id": session_id,
        "inherited_sessions": sorted(inherited_sessions),
        "messages": len(messages),
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "partial_trailing_record_omitted": partial_trailing_record_omitted,
        "coverage": "visible user and assistant text in verified event_msg and response_item/message forms; legacy missing-ID pairs are matched one-to-one within contiguous runs of the same visible role/text across opposite representations, while distinct stable IDs remain separate; excludes system/developer instructions, reasoning, tools, non-text attachments, and unknown message shapes",
        "unsupported": unsupported,
        "excluded_record_types": excluded_record_types,
    }


def render_snapshot(raw: bytes, thread_id: str):
    """Byte-oriented compatibility wrapper; omit an incomplete final JSONL row."""
    if not isinstance(raw, bytes):
        raise TypeError("raw transcript must be bytes")
    trailing = bool(raw and not raw.endswith(b"\n"))
    if trailing:
        raw = raw.rsplit(b"\n", 1)[0] if b"\n" in raw else b""
    return render_lines(raw.splitlines(), thread_id, partial_trailing_record_omitted=trailing)
