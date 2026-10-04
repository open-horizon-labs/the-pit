# Pit harness metrics

Updated 2026-10-04. The connected hosted Pit app is the primary reader/writer. The local companion captures precompaction conversation text into that same account and measures local harness use. Make remains unchanged.

## What is counted

The private SQLite sidecar `~/.local/share/the-pit/metrics/events.sqlite3` records tool, timestamp, success/error, timing, hit count, returned Unicode characters and verified/inserted write outcomes. It never stores inputs, queries, conversation text, entry hashes, credentials or error messages. Session and tool-call IDs provide deduplication. Directory permissions are 0700 and database permissions 0600.

`harness` calls, historical observations, automatic capture, migration and legacy diagnostics are separate origins. Main tool totals and session indicators include harness calls only. Search followed by a range read is a session-level indicator, not proof the calls concern the same result. Characters are not tokens or usefulness. Missing search opportunities are not measured.

PostToolUse observes supported tool names. Because native app calls do not consistently dispatch that callback, Stop and PreCompact also incrementally scan completed Pit MCP tool records in the exact local session. The scanner saves only byte offsets and coverage state, not raw records. Callback and transcript observations deduplicate by session and call ID. Transcript timing is the complete recorded tool duration; until that record is available, hosted `_meta` timing covers the Worker action only. Logging failure never blocks Pit tools or compaction.

The scanner is bounded to 32 MiB per invocation. Partial trailing records remain pending. Truncation, identity mismatch and unsupported completion formats produce incomplete/unavailable coverage rather than zero usage. This is a local transcript-format integration, not a guaranteed public telemetry API. No cloud session coverage is claimed. Successful metrics hooks inject no context.

## Reporting

Run `python3 /Users/drazen/.codex/plugins/cache/the-pit-local/the-pit/0.5.0/metrics/pit_metrics.py` on demand. Coverage cursors are under `~/.local/share/the-pit/metrics/scan-state/`. Metrics remain on this Mac; no retention schedule or remote analytics exporter is installed.

A one-time metadata-only backfill uses `scan_usage.py --backfill`; its observations are labeled `historical`, separately from forward harness use. Backfill scans each session once per invocation and reports pending/unsupported coverage. It never uploads historical conversation text.

## Verification

Tests cover exact session identity, incremental scans, callback/transcript deduplication, private metadata-only storage, partial records, unsupported formats, truncated transcripts, origin separation and capture failure isolation. The hosted Worker adds action timing to all four tools on both success and error; this is response metadata, not persistent server analytics.

41 existing corpus entries (3,010,903 UTF-8 bytes) were copied and verified in the hosted account. Originals remain intact. The migration journal is private and capture writes use the connected app's saved authorization, without copying credentials into the plugin.

Installed verification: all five companion hook definitions were enabled/trusted through native hook discovery. A direct invocation of the installed PreCompact wrapper saved 332 messages (116,761 UTF-8 bytes) with a verified hosted receipt. A real hosted search in this session was observed from its completed harness record at 425.230417 ms. Natural Stop/PreCompact dispatch after the changed definitions is not yet claimed. Restart existing harnesses to load the new definitions.

Historical metadata backfill observed 135 Pit calls: 118 searches, four range reads and 13 writes. One search failed. These include setup/verification activity and are not adoption estimates. Pending bounded scans were completed; 21 older files remained unsupported/unavailable, so historical totals are partial.
