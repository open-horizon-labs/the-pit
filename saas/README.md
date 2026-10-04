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

Refresh/expiry and denial journeys, public directory submission, customer lifecycle and quotas remain unfinished. ChatGPT linking was subsequently verified below. Existing running sessions may need restart to discover the global hosted connection.

## ChatGPT Work trial (2026-10-01)

User-approved public PKCE client `79c0b4f7-d42d-47f2-9a65-2cfb38f16ab4`, named The Pit, uses only `https://chatgpt.com/connector/oauth/4J_YISRQDScM`. Database, Worker and consent allowlists deployed; Worker version `265afab3-a61b-42aa-8544-75ff5a62efc0`. ChatGPT Personal MCP connection `plugin_asdk_app_6abe8a8a55788191887eef2d75091666` completed OAuth consent requesting only offline_access. Actual browser Work sessions verified append (inserted=true, verified=true), then separate-session literal search and bounded range read of exact synthetic text. See [plugin trial notes](plugin/README.md) for receipts.

The hosted package in `saas/plugin` contains two skills and the registered app mapping. Archive import produced Personal plugin `Plugin_a7990534984c819180e58c6840a8bd10`, displaying both skills and one app. This is private testing, not public publication.

Private bundle installation and a combined retrieve/save skill trial passed in a third Work session. Re-saving the exact recovered text returned inserted=false and verified=true with the same hash. Broader skill activation, negative cases and refresh/expiry tests remain pending.

## Public-release preparation (2026-10-01)

See [release checklist](release/README.md). Prepared package 0.1.1 includes square SVG icons; the installed private 0.1.0 bundle is unchanged until re-uploaded. Endpoint throttle and explicit tool annotations are implemented; account export and reviewer password login are implemented but require browser journey verification. Policy pages are drafts. `storage-allowance.sql` is a proposed, locally tested migration, not applied production state. Initial 1 GiB allowance is a configurable proposal, not an agreed per-entry cap. Local SQL verifies UTF-8 accounting, duplicates at capacity, direct-insert rejection and erasure; concurrent trials verify serialized distinct writes and duplicate accounting. Four Worker tests and TypeScript/Vite build pass. Publisher details, production allowance deployment, reviewer account/cases/video, complete erasure workflow and public submission remain pending.

Deployed release-preparation Worker `d91dd809-7fc4-4bc5-a7aa-d5060018ce46`: Cloudflare confirms `PIT_RATE_LIMIT` binding (120 requests / 60s per location). Post-deploy authenticated hosted `pit_search` recovered the existing synthetic trial entry; homepage and OAuth discovery return 200 via curl. Python urllib received 403 on the site; curl/native connector succeeded. Browser rendering and account journeys remain unverified. Account-erasure RPC and feature-gated confirmation UI are prepared; migration unapplied and UI disabled in production. No user data was erased.

## Production release defaults (2026-10-01)

User authorized sane defaults. Applied `storage-allowance.sql` (with RLS on private accounting) and `account-erasure.sql` through the logged-in dashboard after inspecting production: two SaaS entries, largest account 111 UTF-8 bytes. Both existing entries preserved. Production rollback-only fixtures passed UTF-8 accounting, duplicates at capacity, direct-insert quota denial, own erasure, other-tenant preservation, shared identity preservation and OAuth erasure denial. No real user text was erased.

Deployed Worker/site `eb031322-58b7-4ee4-a3e5-76e6face306d`. Initial allowance: 1 GiB per account; no entry cap. Saved text retained until erasure. Signed-in website erasure UI enabled; OAuth tools remain read/append only. Static privacy, terms and support pages are live and fetchable without JavaScript. Policy text explains provider backups and shared authentication separately. Post-deploy authenticated search, exact range and duplicate append passed with unchanged original receipt.

Portable package 0.1.1 includes listing text, icons, policy URLs, five positive and three negative test definitions. It remains a prepared archive, not an uploaded/reviewed/public package. Reviewer account, real browser export/erase/registration/denial/refresh journeys and walkthrough remain incomplete. Browser extension stopped responding after the DB work while the Mac was locked; Supabase CLI has no access token. User asked to unlock before remaining browser steps. Do not use personal OAuth credentials as reviewer credentials or claim the test definitions were executed.

2026-10-02 reviewer setup: user created `pit+review@urch.eu`; dashboard readback confirms account `2788e1bb-8024-461c-bcd2-fbbdd4d24f87`. Native Arc access works while browser-extension requests time out. A separate private Arc window is open for reviewer password sign-in; password remains with the user. Reviewer tools, lifecycle journeys and portal review are not yet verified for this account.


## Harness metrics integration (2026-10-04)

Deployed Worker version `1dc798f8-1210-4ef4-b628-d7af0f10313b`. All four tools return opaque event ID and Worker action duration in MCP `_meta`, on success and failure. No persistent server analytics or raw request logging was added. Five Worker tests and TypeScript validation passed. The local companion measures completed harness tool duration from local records and keeps it separate from capture/migration/history. Static assets were unchanged by this deploy.


## Combined plugin package (2026-10-04)

Prepared portable 0.1.2 archive with hosted tools, three skills, local capture and passive metrics hooks. See [local setup](plugin/LOCAL.md) and [release verification](release/README.md). Hook review/trust opts into local capture; web installation alone does not enable it. Archive verification passed independently of the source tree. This updates the distributable source/ZIP, not the installed private remote bundle or public portal listing.
