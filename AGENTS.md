# Working on The Pit

Read [README.md](README.md) before proposing architecture or implementing changes. Follow the parent workspace instructions and the project's superego guidance at decision points.

## Non-negotiable invariant

**The Pit stores unstructured text. The moment core design starts depending on what the source is, it is drifting.**

- Do not introduce source-specific content types, schemas, parsers, or ingestion branches into the core.
- Do not require source identity, classification, entities, normalized documents, semantic chunks, or projections to accept text.
- Preserve the received text. Keep any interpretation in independent readers.
- Exact-text deduplication is agreed: database-computed SHA-256 identity; personal storage uses `ON CONFLICT (id) DO NOTHING`, while SaaS storage scopes uniqueness to `(user_id, id)` with `ON CONFLICT DO NOTHING`. Repeats keep the original row and first receipt time. Do not add occurrence logs, counts, normalization, or content-quality filtering under the guise of avoiding junk.
- Sinks write directly to a table. Do not add a 50 MB size constraint: the user explicitly removed enforcement when deciding the schema. The figure is a planning reference; database and transport limits still apply. Preserve accepted text without truncation.
- Use the user's estimate that 99% of entries are under 1 MB as the expected workload, not measured evidence. Optimize the common case.
- Keep storage bookkeeping minimal and separate from content interpretation.

## Reading and computation

- Preserve direct reads, range reads, and replay/follow access.
- Agents must be able to build their own search tools, indexes, and transforms over the text.
- A built-in search interface must not become the only read interface.
- Indexes and transformations are reader-owned, replaceable artifacts. Their requirements must not constrain capture.
- Evaluate retrieval speed and computation close to the data without introducing content assumptions into storage.

## Keep the work grounded

- Do not ask the user to choose a source to settle core storage or interface design. Use representative text when a test needs input.
- Keep source-specific adapters outside the core; Make/Zapier mirroring is already an accepted way to get started.
- Do not inherit the structured ingestion model from `durch/intake`.
- Distinguish user-confirmed decisions from assistant proposals. Previously mentioned vendors and stacks remain candidates until selected.
- Record decisions in this folder, including the reason and any evidence. Do not silently turn a proposed design into a system invariant.

## Current implementation and agent handoff

See [hosted implementation and verification](saas/README.md) for the current state and [productization](productization.md) for the wider plan. Historical recommendations are not current deployment instructions.

- Personal Pit: Intake `public.entries`, installed local plugin and Make sink. SaaS: separate `public.pit_entries`, same Intake project, tenant-private exact text. Do not migrate or mix the two corpora implicitly.
- Hosted website and MCP: Cloudflare Worker `the-pit` at `pit.ohlabs.ai`, configuration and code in `saas/auth`. MCP tools: append, literal search, Unicode range read, hash-ordered listing. Listing is a snapshot scan, not a commit-ordered follow cursor.
- OAuth: Supabase email sign-in and server enabled; Google/GitHub and dynamic client registration disabled. The registered public Codex client is explicitly allowlisted in PostgreSQL, Worker and consent UI. UI allowlisting alone is not authorization.
- JWTs require the exact resource audience `https://pit.ohlabs.ai/mcp`. The token hook changes only enabled Pit client tokens; unrelated sessions retain their claims. Worker passes the caller token to the Data API and uses only a publishable key. Never add a service-role bypass.
- Native Codex `pit_hosted` connection is configured locally. Its exact registered callback is `http://127.0.0.1:43179/callback/_ON0xvzJpibU`; callback URL and port must be pinned. Bare `codex mcp add` starts another flow with a random port and can produce `invalid redirect_uri`. Local OAuth credentials and config are not repository artifacts; never inspect/print tokens or the personal Pit connection file.
- Verified: live rollback-only two-tenant isolation, per-tenant exact dedup, Unicode ranges, denied ownership spoof/update/delete/anonymous and unknown-client access; real email login and consent; native authenticated hosted append/dedup/search/range/list including custom-audience Data API acceptance.
- Still unverified/unbuilt: production ChatGPT linking, fresh login using saved pinned configuration, refresh/expiry and consent denial journeys, directory publication, quotas/billing and complete customer lifecycle. Do not call this a public SaaS launch.
- Applied SQL in `saas/tenant-storage.sql` and `saas/enable-codex-client.sql` is a deployment record, not an idempotent migration runner. Inspect live state before applying any SQL. `saas/tests/bootstrap.sql` is disposable local PostgreSQL only; live policy tests roll back their fixtures.
- Build/test: `cd saas/auth && npm ci && npm test && npm run build`. Deploy with `npm run deploy` only within the current authorized scope; production frontend env is private and ignored. The Worker config's Supabase publishable key is public, not a secret. Do not rotate credentials or signing keys to resolve setup errors.

This folder is the Git repository boundary. Keep dependencies, build outputs, local credentials, caches and unrelated ai-omnibus projects out of commits.
