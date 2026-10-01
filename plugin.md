# Export to Pit plugin

## Installed and connected — 2026-09-30

The local plugin `the-pit@the-pit-local` is installed and enabled, version **0.4.0**. It bundles an [export skill](plugin/skills/export-to-pit/SKILL.md) and Python 3 helpers without third-party dependencies. Say **“Export this session to Pit”** in a local Work/Codex conversation where the skill is available. The user also authorized automatic export before compaction for **all local sessions**, across workspaces. The local Work runtime discovers both the skill and the PreCompact hook. Restart an existing harness to load the updated installation. This is a local installation, not a published plugin or a cloud Work integration.

The plugin sends only `content` to `public.entries` in Supabase project `iunbpyiylsbkscjaisid`, using the HTTP Data API. It compares the stored text with its saved snapshot before reporting success. Identical snapshots leave the original row and receipt time unchanged. Reads by content hash are available through `pit_client.py --read HASH`; this does not constrain future search tools.

## Access

A dedicated Supabase Auth account has read and content-only insert access to `entries`. [Table grants](access.sql) and [account policies](client-policy.sql) were applied live. Anonymous access, updates, deletes, and supplied receipt timestamps are denied. A database administrator retains administrative capabilities.

The plugin stores its publishable API key and refreshable user session in `~/.config/the-pit/connection.json` (file `0600`, directory `0700`). Never print that file or put it in source control. Token rotation was verified live. The [one-time bootstrap](provision_client.py) used the signed-in Supabase CLI; the admin key was held only in memory, and the generated password was deleted after sign-in. No admin credential is bundled with the plugin.

These checks establish the permissions on **entries**, not isolation across the whole existing Intake project. The account uses the ordinary `authenticated` role; other tables' existing grants and policies govern any access there. Other intake tables were not changed.

## Export and recovery

The exporter selects the current thread by `CODEX_THREAD_ID`, never the newest file. It reads a fixed snapshot of the matching local JSONL record and saves completed user/assistant text, including assistant commentary, in recorded order. Text inside messages is preserved; speaker labels and separators are added by the exporter, outside the Pit core.

Snapshots are created as private files under `~/.local/share/the-pit/exports/`. Uploads preserve this file before sending, so uncertain delivery can be recovered using the same bytes. Use `pit_client.py --verify-file ABSOLUTE_PATH` for a quiet local comparison. It reports only identity, match status, and receipt time. If the entry is absent after a successful check, `--append-file ABSOLUTE_PATH` retries that exact snapshot safely through hash uniqueness. Do not generate a fresh export as a retry.

Tool events, attachments, system/developer instructions, and hidden reasoning are excluded. Non-text message parts, unknown phases, corrupt complete records, and conflicting repeated message IDs fail explicitly. A partial trailing record is reported and omitted. This is a conversation-text snapshot, not a complete execution archive. Edited/forked histories and UI completeness across client versions remain unverified. Local disk format compatibility is not a stable published export API. Cloud Work needs its own verified transcript-access path.

## Live evidence

On 2026-09-30, this conversation's snapshot was uploaded and read back exactly:

- 157 completed messages; 65,761 UTF-8 bytes.
- Entry ID: `aa8518eb7066edb20a8084a3f8ddd143b0e48451a4878f2b8ed03787261822d8`.
- Receipt: `2026-09-30T21:29:40.163292+00:00`.
- An identical resubmission returned the existing row and the same receipt timestamp.
- Anonymous reads/writes, authenticated updates/deletes, and attempts to supply `received_at` were rejected.
- Auth refresh and subsequent reads succeeded with private file permissions preserved.
- 15 automated exporter/client tests pass, including quiet recovery comparison.

The earlier snapshot predates later setup messages. See the newer hook verification below.

References: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Work local security](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-local-security), [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys).

## Automatic export before compaction

Version 0.4.0 bundles a synchronous `PreCompact` command hook for both `manual` and `auto`. It is enabled and trusted globally for all supported local Work/Codex sessions; there is no workspace restriction. Cloud is out of scope. The hook calls deterministic Python code without invoking a model or asking the model to reproduce text.

The host event supplies the session identity and transcript path. The wrapper validates a UUID and the actual transcript metadata/format before capture. A missing path uses exact-session rollout discovery; a malformed path or unsupported transcript fails visibly without uploading another conversation. Coverage is the same completed text as the manual exporter. Chats that never compact are not automatically captured, and attachments/unsupported formats still fail explicitly.

The hook writes and fsyncs a private text snapshot and a separate local receipt before attempting delivery. The receipt initially records unknown delivery and is updated only after exact readback. It invokes the client with a 10-second request timeout and a 45-second total child-process limit, inside a 90-second host hook timeout. It never retries an uncertain append automatically. Failures report the recoverable snapshot and return `continue: true`; a hard host termination cannot return a structured response, and its saved receipt remains unknown. No transcript or credentials are emitted in hook output. These receipt files are exporter bookkeeping, not additional fields in the Pit table.

### Verified on 2026-09-30

- The app's bundled Codex 0.159.2 lists the hook as enabled and trusted in both this workspace and `/tmp`.
- Trust was recorded for the exact definition/hash emitted by `hooks/list`, through the app server's narrow configuration-write API. No trust-bypass option was used; unrelated hooks were left unchanged.
- A direct invocation of the installed hook with this session's identity/path saved 178 messages, 71,654 bytes, and verified exact Supabase readback.
- Entry ID: `44ab88426e5e702016555f805e8c29aa1e578adad65379be99b9ab50f70a565e`; receipt `2026-09-30T21:53:18.65183+00:00`.
- 20 tests pass, including private save before transport, unsupported identity/format, stdin failures, retained snapshots after timeout, and no automatic retry or text leakage.
- An actual host-triggered PreCompact event is still awaiting the next natural compaction after a harness restart. The direct invocation above is not evidence that the live event has fired.

The package uses `.codex-plugin/plugin.json`, the supported Codex compatibility layout. Live discovery failed with the portable root `plugin.json`; the inspected OpenAI loader skips plugin hooks for that format. The compatibility package was discovered successfully. Keep this packaging choice until the installed runtime verifies portable-hook support.

To inspect or disable the hook, use the host's hook management (`/hooks` in the CLI). Changed definitions require a new trust review. To recover uncertain delivery, use the installed client's `--verify-file` with the saved snapshot path. See [hook documentation](https://learn.chatgpt.com/docs/hooks).

## Reader deployment, 2026-10-01

Plugin 0.4.0 installed and its search/range RPCs live-verified. Native Work discovery confirms the global PreCompact hook enabled and trusted in this workspace and /tmp, without errors or warnings. The installed hook definition hash is unchanged. Database verification confirms a valid trigram index and SECURITY INVOKER functions, authenticated EXECUTE and denied anonymous EXECUTE. A natural host-triggered compaction remains unverified; the recorded successful hook trial was manual.

## Retrieval adoption — installed 0.5.0, 2026-10-01

The compatibility manifest now includes .mcp.json. The local stdio server runs Python from the installed plugin root using cwd "./", avoiding unsupported compatibility-format PLUGIN_ROOT argument expansion. It exposes only pit_search and pit_read_range, marked read-only, using the existing private Client and database functions. No additional database privileges or canonical columns were added.

The retrieve-from-pit skill advertises continuing earlier work, prior decisions and missing compaction context. The global ~/.codex/AGENTS.md adds conditional retrieval guidance while preserving the prior file content.

PostToolUse matches only mcp__pit__pit_search and mcp__pit__pit_read_range. It retains up to eight validated immutable entry/range anchors per exact host session. PreCompact adds a last-verified capture tail only after exact upload verification. SessionStart on startup/resume/compact restores bounded metadata and retrieval guidance. No retrieved excerpts or queries are promoted into developer context. State files are private and reader-owned, outside the Pit table. Hook failures remain nonblocking; unknown upload never becomes a verified pointer.

Native Work plugin/read discovered both skills and the Pit MCP server. MCP inventory discovered both tools with no toolsError; all three hook definitions are enabled and trusted in this workspace and /tmp. A fresh read-only ephemeral CLI trial asked what we decided about sources without naming a tool: the model chose two searches and a range expansion, answered from the user's earlier corrections, and real PostToolUse events wrote anchors under that trial session.

A separate ephemeral native app-server trial seeded a real hash/range after its first model turn, then compacted through the host. The following model turn reported the exact pointer [24001,24123), despite it never appearing in pre-compaction model history. This verifies SessionStart compact delivery, not merely script output. Ephemeral sessions do not have a supported export rollout; this test does not prove automatic transcript upload. Capture handler tests and the previous manual export proof remain distinct.

Existing running chats may require a harness restart to discover the newly installed direct tools and hooks. The retrieval skill's bounded command fallback remains available. Broader spontaneous use across different models and real tasks will be observed during normal work.

## Direct text writes (2026-10-01)

`pit_append(content)` exposes the existing exact-text append client to local Work/Codex. Its description encourages saving useful briefs, findings, decisions, experiment results and notes. No source metadata or schema is required. Exact duplicates are ignored; the response contains a content hash, receipt time, insertion status and exact-text readback verification. Source and installed 0.5.0 were updated; restart the harness to discover the new tool. Automatic conversation capture remains separate.
