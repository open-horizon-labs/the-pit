# Pit call metrics

Implemented 2026-10-01 in source and installed local plugin 0.5.0.

The MCP server records tool, UTC timestamp, success/error, elapsed milliseconds, search hit count, returned Unicode character count, and verified/inserted write outcomes in a private SQLite sidecar at `~/.local/share/the-pit/metrics/events.sqlite3`. Queries, entry text, content hashes, credentials and error messages are not stored. Directory permissions are 0700 and database permissions 0600. Logging is best effort; failures never block Pit calls. No metrics are injected into model context or written to the Pit corpus.

A filtered PostToolUse hook records session, turn and call identifiers. An opaque event UUID in MCP `_meta` joins the hook observation to the measured execution. Unlinked observations remain visible rather than guessed. Server executions and hook observations are separate counts, not added together. Repeated hook call IDs are deduplicated. Searches followed by later range reads in the same observed session are reported as a session-level indicator, not proof they concern the same result. Characters measure retrieval volume, not tokens or usefulness. No-call sessions and missed search opportunities are outside this log's coverage.

Report on demand:

```sh
python3 /Users/drazen/.codex/plugins/cache/the-pit-local/the-pit/0.5.0/metrics/pit_metrics.py
```

Verification: unit tests cover private metadata-only storage, hook linking/deduplication, missing metadata, error records and logging failure isolation. A real installed-server search returned one hit, 88 characters and a metrics receipt, with measured elapsed time about 392 ms. The initial database also contains one diagnostic error from the pre-isolation test run; these initial two calls are setup evidence, not agent adoption data.

Session attribution was tested with synthetic hook events, not yet live Work callbacks. Restart the harness and review/trust the changed plugin hook definition, then run a real Pit call and check `hook_observations` and `linked_observations`. Until then, per-session coverage is unverified. Existing capture remains unchanged. The MCP process must reload to use server instrumentation. No historical transcript backfill is performed. Metrics currently stay on this Mac and grow until manually cleared; no retention scheduler or remote exporter is configured.
