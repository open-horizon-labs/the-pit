# Local capture and usage metrics

Version 0.1.3 bundles the hosted tools, three skills, local history collector and five hook handlers. Local hooks are supported by ChatGPT Work/Codex when the package scripts are present in the local execution environment. Installing on the web alone does not deploy them. Cloud capture is unsupported.

## Requirements and setup

- Python 3, the `codex` executable on PATH, and a connected/authorized hosted Pit app in the same local harness profile.
- A supported local transcript with an exact session identity under CODEX_HOME (default ~/.codex).
- Tested on macOS. Native transport uses POSIX pipes and the availability helper uses fcntl; Windows is not currently supported by this package.
- Disable the separate `the-pit@the-pit-local` companion before enabling these hooks. Keep only one copy active.
- Inspect the package's hooks/hooks.json through the harness hook review UI (`/hooks` in CLI). Installation does not automatically trust hooks. Review and trust desired handlers; changed definitions require review again. Restart an existing harness after updating the package.

## Before enabling automatic capture

Trusting the PreCompact capture handler opts into uploading completed user and assistant conversation text before **every automatic or manual compaction in local sessions where this plugin and hook are enabled**, across workspaces. The destination is your connected hosted Pit account. This is not limited to conversations that mention The Pit. Text includes assistant progress messages; tools, attachments, hidden reasoning and system/developer instructions are excluded. Local transcript format is not a guaranteed public export API; unsupported records fail visibly. Chats that never compact are not automatically captured.

Capture saves a private snapshot and receipt before upload, then checks the exact-text hash receipt. No model turn is invoked and saved app authorization is consumed by the native runtime, not copied into the plugin. Unconfirmed delivery retains the snapshot and warns while allowing compaction. Disable the PreCompact **capture** handler to stop automatic uploads; leave the separate metrics handler enabled if desired. A manual export still requires an explicit export request.

Before saving private text, complete the own-account save/search checks in INSTALL.md. The current app registration is a developer trial; independent account installation is not yet verified.

## Explicit all-history collection

`skills/export-to-pit/scripts/harvest_history.py` is an opt-in local command for collecting visible text from existing Codex rollout files. It scans `~/.codex/sessions` and `~/.codex/archived_sessions`; configured remote coder targets can be added explicitly. It sends rendered user/assistant text through the connected hosted Pit app using its saved authorization. The collector does not install a hook or start a background service by itself.

Run one pass with `python3 "<installed plugin root>/skills/export-to-pit/scripts/harvest_history.py" --once`. The local source uses `~/.codex`, or the path passed with `--codex-home`; its stable source label can be changed with `--source-id`. A configured remote account can be added with `--coder-target personal.stock` or `--coder-target personal.assembler`; remote scans use that account's `~/.codex` directory. Use only targets already configured for the intended accounts. Repeated collection can run with `--interval 300` (the default) under a process supervisor chosen by the user. The private SQLite checkpoint is stored at `~/.local/state/the-pit/harvest.sqlite3`; it contains source/session/path metadata, hashes, verified entry IDs and parser coverage. Uploaded headers include the source ID, session UUID and session start when available; local filesystem paths stay in the checkpoint. Messages may include `Recorded at` labels from their rollout record timestamps; these mark when the source recorded the message, not when the described activity happened. If delivery is uncertain, it temporarily retains the exact pending text and retries those bytes before rescanning; pending text is deleted only after a verified receipt. The command prints aggregate outcomes and does not print transcript contents. `--once` exits nonzero if a source or transcript operation failed; unsupported or empty sessions are reported separately.

The source timestamp in the header is labeled as session start. Per-message `Recorded at` labels, when present, come from each rollout record and indicate when the source recorded it, not when the described activity happened. Coverage is limited to verified visible text forms in local rollout records. Tool events, hidden reasoning, attachments and unsupported content are excluded and reported in coverage. Forked rollouts are accepted only when their session metadata explicitly links the inherited parent. Legacy missing-ID pairs are matched one-to-one within contiguous runs of the same visible role/text across opposite representations; distinct stable IDs remain separate, and ambiguous legacy formats remain best effort. Changed or newly supported rendering is rescanned when the parser fingerprint changes; exact-text deduplication avoids a second Pit entry when rendered text is unchanged. This command has not been run against production history as part of package preparation.

## Usage measurement

PostToolUse observes Pit calls. Stop and PreCompact incrementally inspect completed Pit tool records for the exact local session because some native calls bypass callbacks. They save only tool name, timestamp, outcome, timings, hit count, returned character count, write outcomes and session/call identifiers. No queries, input text, retrieved text, entry hashes, credentials or error messages are persisted in metrics. Callback and transcript observations deduplicate by session and call ID.

Automatic captures, migrations and historical observations are separated from forward harness calls. No migration or historical backfill runs on installation. Stop does not upload conversation text or metrics. A bounded scan reads at most 32 MiB of local records per invocation; partial or unsupported coverage is reported instead of interpreted as zero. Transcript timing covers recorded tool duration; response metadata initially covers only the hosted Worker action.

Report with `python3 "<installed plugin root>/metrics/pit_metrics.py"`. Characters are not tokens, relevance or proof of usefulness. Missed opportunities to search are not observable from call counts.

## Private local files

Snapshots/receipts: ~/.local/share/the-pit/exports/

Metrics/cursors: ~/.local/share/the-pit/metrics/

Capture bookmarks: ~/.local/share/the-pit/retrieval/ (not automatically hydrated into context).

These are per-user files, not shipped package contents. Private directories use mode 0700 and files 0600. Metrics have no remote upload or automatic retention schedule. The SessionStart hook supplies only a short availability reminder, without fetching previous sessions.

Official references: https://developers.openai.com/plugins/build/plugins and https://learn.chatgpt.com/docs/hooks .
