---
name: export-to-pit
description: Export the current local ChatGPT Work or Codex conversation to The Pit when the user asks to export or save the session, or retrieve a Pit entry by its content hash. For missing prior context, use the retrieve-from-pit skill.
---

# Export to Pit

The local companion writes through the connected hosted Pit app, using the native Codex app-server and its saved authorization. The bundled `hosted_client.py` invokes the hosted tool without a model call. Never inspect or print credentials or the legacy connection file. If native app authorization is unavailable, report capture as unconfirmed; do not silently write to the original personal database.

Use the bundled `scripts/export_session.py` with Python 3. Resolve the script relative to this skill directory. Run `--check` first. It selects the current session using `CODEX_THREAD_ID` and searches `CODEX_HOME/sessions` and `CODEX_HOME/archived_sessions` (default `~/.codex`). If the current session identity or record is unavailable, explain that local export is unsupported there. Do not choose the newest file or a different conversation. An explicitly user-selected record can be passed with `--rollout PATH --thread-id ID`.

For “Export to Pit”, run the script with `--upload`. It saves a private snapshot under `~/.local/share/the-pit/exports/`, then appends only its text to the hosted Pit account. It reads the entry back and compares exact content before reporting success. An export request authorizes this upload; do not request permission again for the same destination. Report the returned ID and message/byte counts. An identical snapshot keeps its original receipt timestamp.

For a local-only export, use `--output ABSOLUTE_PATH`, selecting a new file in the private exports directory. Create the directory with mode `0700` if needed. Use a project directory only when the user selects it.

When the user explicitly asks to collect existing Codex history or keep local/selected remote history flowing into the Pit, use `scripts/harvest_history.py`. Start with `--once` to inspect aggregate source counts and coverage; add each configured remote with `--coder-target TARGET`. For ongoing collection, run it without `--once` and use a user-selected process supervisor. The collector uses the connected hosted Pit authorization, saves a private resumable checkpoint, and reads each target's active and archived `~/.codex` rollout directories. It does not install another hook or begin collection at package installation. Retry collector failures with the same checkpoint path so its saved outbox is delivered before new snapshots are scanned. Uploaded headers identify the source, session UUID and session start when available; local file paths remain checkpoint metadata.

The collector preserves visible text in supported rollout message forms, skips non-text parts while retaining text parts, and reports exclusions. Forked histories require explicit session metadata links. Legacy missing-ID forms are paired one-to-one within contiguous runs of the same visible role/text across opposite representations; distinct stable IDs remain separate, and ambiguous old records remain best effort.

If delivery is unknown, preserve the snapshot and its hash. Use `hosted_client.py --verify-file ABSOLUTE_PATH` to fetch and compare locally; it returns only the hash, match status, and receipt time. Do not use `--read` for routine recovery, because that command prints the stored text. Do not generate a new snapshot as a retry. If verification returns `found: false` after a successful read, the existing snapshot can be sent with `hosted_client.py --append-file ABSOLUTE_PATH`; hash uniqueness makes identical retries safe. Missing configuration or denied access is a failed connection, not a successful export.

Use the connected hosted `pit_search` and `pit_read_range` tools for context retrieval. The basic read interface remains open to independent search tools.

Coverage is the completed user and assistant message text recorded in the local session, including assistant progress messages. The script reads recorded text deterministically. Do not summarize, rewrite, reconstruct from model context, or substitute a thread summary. It excludes tool events, attachments, hidden reasoning, and system/developer instructions. This is a conversation-text snapshot, not a complete execution archive. If the user requires other contents, explain the current limitation before claiming completeness.

Manual exports run only on a user's export request. The bundled PreCompact hook is available for supported local execution only. Before trusting it, users must understand that automatic and manual compaction will upload completed user/assistant conversation text from every local session where the plugin and hook are enabled, across workspaces, to their connected Pit account. Installing the plugin alone does not authorize or enable automatic capture. Review and trust the exact hook definition to opt in; disable the PreCompact capture handler to stop it. Cloud is out of scope. Do not apply the publisher's personal capture authorization to another user.

The hook validates the exact session identity and supported transcript format, saves a private snapshot before upload, and reports unconfirmed delivery while allowing compaction to continue. Do not manually export unrelated sessions or add capture triggers. Near-duplicate snapshots are accepted; exact-text deduplication belongs to the Pit. Keep transcript parsing in the exporter and pass only text into the Pit write interface. See LOCAL.md at the package root for requirements, private state and hook setup.

## Database readers

Start with the hosted `pit_search` tool: five entries and 500 surrounding characters by default. Expand relevant anchors with `pit_read_range`, at most 20,000 Unicode characters per call. Offsets are zero-based and half-open. Never fetch full sessions by default. Readers respect account isolation.
