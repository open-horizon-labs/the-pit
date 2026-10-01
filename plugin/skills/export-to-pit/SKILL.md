---
name: export-to-pit
description: Export the current local ChatGPT Work or Codex conversation to The Pit when the user asks to export or save the session, or retrieve a Pit entry by its content hash. For missing prior context, use the retrieve-from-pit skill.
---

# Export to Pit

The plugin uses Supabase's HTTP Data API with a dedicated Auth session in `~/.config/the-pit/connection.json`. The bundled `pit_client.py` manages token refresh. Credentials are never passed as command arguments or tool arguments. Never print or read the connection file into model context.

Use the bundled `scripts/export_session.py` with Python 3. Resolve the script relative to this skill directory. Run `--check` first. It selects the current session using `CODEX_THREAD_ID` and searches `CODEX_HOME/sessions` and `CODEX_HOME/archived_sessions` (default `~/.codex`). If the current session identity or record is unavailable, explain that local export is unsupported there. Do not choose the newest file or a different conversation. An explicitly user-selected record can be passed with `--rollout PATH --thread-id ID`.

For “Export to Pit”, run the script with `--upload`. It saves a private snapshot under `~/.local/share/the-pit/exports/`, then inserts only its text into `entries`. It reads the entry back and compares exact content before reporting success. An export request authorizes this upload; do not request permission again for the same destination. Report the returned ID and message/byte counts. An identical snapshot keeps its original receipt timestamp.

For a local-only export, use `--output ABSOLUTE_PATH`, selecting a new file in the private exports directory. Create the directory with mode `0700` if needed. Use a project directory only when the user selects it.

If delivery is unknown, preserve the snapshot and its hash. Use `pit_client.py --verify-file ABSOLUTE_PATH` to fetch and compare locally; it returns only the hash, match status, and receipt time. Do not use `--read` for routine recovery, because that command prints the stored text. Do not generate a new snapshot as a retry. If verification returns `found: false` after a successful read, the existing snapshot can be sent with `pit_client.py --append-file ABSOLUTE_PATH`; hash uniqueness makes identical retries safe. Missing configuration or denied access is a failed connection, not a successful export.

Use the database readers below for context retrieval; use `pit_client.py --read HASH` only for an explicit full-text request. `pit_client.py --status` checks connectivity without returning corpus text. This basic read path does not constrain future independent search tools.

Coverage is the completed user and assistant message text recorded in the local session, including assistant progress messages. The script reads recorded text deterministically. Do not summarize, rewrite, reconstruct from model context, or substitute a thread summary. It excludes tool events, attachments, hidden reasoning, and system/developer instructions. This is a conversation-text snapshot, not a complete execution archive. If the user requires other contents, explain the current limitation before claiming completeness.

Manual exports run only on a user's export request. The user also authorized the bundled PreCompact command hook for all supported local sessions: automatic and manual compaction save completed conversation text without a model call. The hook must be enabled and trusted by the host; cloud is out of scope. It validates the exact session identity and supported transcript format, saves a private snapshot before upload, and reports unconfirmed delivery while allowing compaction to continue. Do not use this authorization to export unrelated sessions manually or add other automatic triggers. Near-duplicate snapshots are accepted; exact-text deduplication belongs to the Pit. Keep source-specific parsing in this exporter and pass only text into the Pit write interface.

## Database readers

For context retrieval, start with pit_client.py --search "literal phrase". This returns the first case-insensitive literal match per entry, newest first, five entries by default with 500 characters on each side. Set --limit (1 to 20) or --context (0 to 2000) as needed. Follow anchors with --range HASH START END (at most 20,000 characters). Offsets are zero-based Unicode code points, half-open [START, END), clamped at EOF. Matching and slicing happen in Postgres before transfer. Reserve --read HASH for explicit full-text requests. Empty results mean no matching accessible entry. Both readers respect existing RLS.
