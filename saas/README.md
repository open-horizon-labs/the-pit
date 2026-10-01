# Hosted Pit prototype

## Applied 2026-10-01

Existing Intake project `iunbpyiylsbkscjaisid`; website and remote MCP hosted at `https://pit.ohlabs.ai`. Existing personal `public.entries`, local plugin and Make sink remain separate. No personal corpus was migrated.

`tenant-storage.sql` applied with user approval. SaaS content table `public.pit_entries` contains `user_id`, generated exact-text SHA-256 `id`, first `received_at` and original `content`. Primary key `(user_id,id)`. Column grants reserve identity, ownership and receipt fields for the database. RLS enforces owner read/append; no normal update/delete privileges. Auth user deletion cascades to this corpus as an account-erasure exception, not an ordinary content operation.

`public.pit_oauth_clients` contains public client IDs and enabled flags only. OAuth data access requires an enabled client in this table. Direct signed-in user sessions may access their own rows. Only administrators can change the allowlist. The enabled `public.pit_access_token_hook` sets audience `https://pit.ohlabs.ai/mcp` only for enabled Pit clients; all other token claims remain unchanged. No existing hook or signing key was replaced.

Built-in readers remain replaceable: literal search and Unicode ranges execute in PostgreSQL; hash-ordered listing allows independent scans. Direct authenticated Data API reads are available under the same RLS. Listing is not a commit-ordered follow cursor. No source fields, normalization, semantic chunks or application text-size cap.

## Worker

Implementation in `auth/worker/index.ts`, maintained MCP SDK 2.2.0, web-standard HTTP handler and Cloudflare schema validator. Routes:

- `/mcp`: authenticated MCP, tools `pit_append`, `pit_search`, `pit_read_range`, `pit_list`.
- `/.well-known/oauth-protected-resource/mcp` (and root variant): OAuth discovery.
- Other paths: static account/consent SPA.

Worker verifies asymmetric signature, Intake issuer, exact MCP audience, expiry, authenticated role, user subject and explicit client allowlist. Database requests use the caller's token and a publishable key, never a service-role key. Append returns a database-side exact-text verification receipt and preserves original receipts on duplicates. Request bodies and tokens are not logged by application code. Failed requests do not imply a successful write.

Current deployed version `e30b1201-5326-491e-9d0b-a001f96ab895`. Live discovery returns the correct resource and issuer; missing credentials receive 401 and discovery challenge; site returns 200.

## Codex linking trial

Manually registered public PKCE client “The Pit — Codex”, ID `24ac42eb-bd23-4fae-8eb1-540e4cefe213`. Exact redirect `http://127.0.0.1:43179/callback/_ON0xvzJpibU`. User approved enabling it; database, Worker and consent UI allowlists agree. Dynamic client registration remains off. Consent text states actual read/append permissions.

The user completed sign-in and consent; `codex mcp login` confirmed success. Native app-server tool calls using saved OAuth credentials verified token exchange, custom-audience Data API acceptance and all four remote tools. Global `pit_hosted` is installed with the fixed callback URL/port. A second automatic flow from `codex mcp add` used an unregistered random port, produced `invalid redirect_uri`, and was cancelled; the callback is now pinned. The successful credential remained usable. No production ChatGPT client has been registered: obtain its exact callback URI from the MCP management page rather than guessing or using a wildcard.

## Verification

- Local PostgreSQL 16 migration and isolation checks pass.
- Live Intake rollback-only test passes: two accounts can store identical text independently; exact duplicates ignored; cross-account search/range/list isolation; unknown OAuth clients denied; anonymous RPC denied; updates/deletes and ownership spoof denied; Unicode range preserved; audience hook changes only enabled clients. Live dashboard restricts impersonating `supabase_auth_admin`; hook behavior was checked as database administrator; real OAuth token issuance and Data API acceptance subsequently passed.
- Three Worker tests pass: discovery/auth boundary; signature/issuer/audience/expiry/client/role enforcement; real SDK legacy initialization and tool listing.
- TypeScript build and Wrangler bundle/deployment pass.

Run Worker tests with `cd auth && npm ci && npm test`. SQL fixtures in `tests/bootstrap.sql` are for a disposable local PostgreSQL only; `tests/isolation-live.sql` is the rollback-only dashboard trial. Do not run the bootstrap against Intake.

## Authenticated native trial

2026-10-01: saved OAuth credentials consumed by native `mcpServer/tool/call`, without inspecting tokens or invoking a model. First append verified and inserted; identical repeat verified with inserted=false and unchanged receipt. Search found the entry; range returned exact original text including Unicode and literal backslash-n; listing returned its hash/receipt/length. Hash `8130217d99f50a430a8f7c4362f937016e2f3e19c83aac0502076f822f3ecc25`, receipt `2026-10-01T15:02:05.721047+00:00`. One synthetic verification entry remains. A preceding model-driven CLI attempt failed because its configured model was unsupported by the ChatGPT account and performed no tool calls; no model was substituted.

Production ChatGPT linking, refresh/expiry and denial journeys, directory package/submission, customer lifecycle and quotas remain unfinished. Existing running sessions may need restart to discover the global hosted connection.
