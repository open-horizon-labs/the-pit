# The Pit SaaS — productization plan

2026-10-01. User requested aggressive productization as a small SaaS and public ChatGPT plugin. This is a proposed implementation sequence, not a deployed product or approved pricing plan.

## Aim

People save useful work from one AI session and recover original context in later sessions without manually rebuilding it. Initial customer hypothesis: individual heavy AI users producing briefs, research, decisions and experiment notes. Observable success: a new user connects, saves text, and independently retrieves it in another chat; then repeats this on later days. Retention and willingness to pay remain untested.

## Product contract

Exact unstructured text, tenant-private by default, append-only normal operations, exact duplicates ignored within a tenant. No content model, classification, source field, semantic projection or mandatory embeddings. Account ownership and access bookkeeping are separate from content meaning. Search is one reader; raw reads, range reads, enumeration and export remain available for independent tools. Follow/replay semantics need explicit implementation and verification; receipt timestamp alone is not a reliable commit cursor.

Trust compaction summaries. Retrieval is for specific missing context. Writes require the user's authorized workflow; directory tool descriptions must not induce unauthorized transfers. A private user's standing frequent-write preference is not automatically every customer's consent.

## Recommended first offering

A private Pit account with hosted append, literal search and range reads, connected through a public remote MCP plugin. Small website for account signup, connection instructions, text paste/import, usage, API credentials, export and account controls. Begin with a single personal account; team sharing and a marketplace for reader programs can wait.

Existing code is a single-user reference, not yet a SaaS: local stdio MCP, dedicated Supabase auth session, exact append/readback, bounded database readers and local capture hooks. Preserve existing personal setup. Build isolated SaaS migrations and deployment, without repurposing legacy Intake tables or sharing personal credentials.

## Build sequence and acceptance

1. **Tenant storage and authorization.** Continue with PostgreSQL/Supabase as the preferred storage family. Model ownership separately, scope hash uniqueness to a tenant, enforce isolation on writes, reads, search, ranges, enumeration and export. Tenant identity comes from verified credentials, never caller-selected ownership. Test two tenants including identical text and attempted cross-tenant reads. Do not globally deduplicate across customers in a way that leaks existence or complicates deletion.
2. **Hosted interface and account linking.** Expose append/search/range via HTTPS remote MCP and offer documented raw read/list/export access. Use a maintained MCP transport implementation. Select a managed OAuth authorization server only after verifying authorization-code/PKCE, discovery, client registration compatibility, audience/scopes and revocation. Verify actual ChatGPT connection, token expiry and error behavior. Do not assume the current local password session meets remote MCP OAuth requirements.
3. **First real customer journey.** Signup -> connect -> save a brief -> new chat -> find and recover original text -> export it. Exact-text receipts and harmless duplicate retries. No raw text in routine request logs. Verify latency and representative entry sizes, quota accounting, backup/restore and deletion behavior. No arbitrary text truncation.
4. **Small paid beta.** Subscription with stated storage/query allowance and transparent limits is a pricing hypothesis; no price or unlimited promise selected. Instrument storage bytes, query load and infrastructure cost separately from text. Confirm repeat retrieval and payment interest before expanding capture integrations. Billing and launch publisher remain open decisions. Domain and hosting are now selected: `pit.ohlabs.ai` on Cloudflare Workers.
5. **Directory submission.** Prepare remote MCP package, focused skills, real endpoint, verified publisher/domain, website/support/privacy/terms links, reviewer access, example prompts and reproducible review journeys. Automated checks and review precede publication; approval is not guaranteed.

## Capture and account lifecycle

The public SaaS plugin accepts text supplied in authorized tool calls. Do not advertise automatic full cloud-chat capture. Existing PreCompact export is a local companion with separate installation/authorization; cloud transcript capture remains out of scope.

Normal content operations stay append-only. A production SaaS still needs explicit customer retention, erasure and account-closure behavior. Decide this operational exception before accepting customer data; do not silently introduce normal edit/delete tools or promise permanent retention. Revoking plugin access and deleting stored data are distinct actions.

## Official distribution evidence checked 2026-10-01

- [Submission](https://developers.openai.com/plugins/deploy/submission): plugins may include remote MCP and skills; current submission excludes lifecycle hooks. Publishing requires verified identity, MCP/domain setup and review. Attached MCP listings require website, support, privacy and terms URLs.
- [Authentication](https://developers.openai.com/plugins/build/auth): remote MCP OAuth requires discovery, authorization-code + PKCE and server-side validation of issuer, audience, expiry and scopes. Choose a provider against these requirements.
- [Guidelines](https://developers.openai.com/plugins/plugin-guidelines): a clear useful purpose, reliable complete behavior and actions within user-authorized tasks. No promise of native directory billing or guaranteed listing.

## Immediate milestone

An isolated two-account hosted Pit prototype with working ChatGPT OAuth linking and the save/recover/export journey. This validates the two biggest gaps: safe multi-user ownership and directory-compatible remote access. The auth website is deployed; the two-account journey, customer enrollment and directory submission remain unfinished.

## Supabase consolidation — 2026-10-01

The user proposed Supabase Auth, one logical database and a read replica. Official docs confirm Supabase Auth can serve OAuth 2.1/PKCE with MCP discovery and dynamic registration, using existing users and RLS. Select this as the first integration to prove end-to-end, including consent UI and token audience/client access checks; account linking is not yet tested.

Architecture: one SaaS Supabase project, primary PostgreSQL for appends, immediate exact-text receipt verification, account/auth operations and freshness-sensitive reads. A read replica can serve historical searches/ranges to isolate read load; asynchronous replication means it can temporarily miss new entries. Replica Data API supports GET only, so existing POST reader RPC calls must remain on primary or use supported read-only GET RPC/direct database routing. Auth stays on primary. Enable replica when measured load warrants it; no replica or new project has been provisioned.

References: [OAuth server](https://supabase.com/docs/guides/auth/oauth-server), [MCP authentication](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication), [Read replicas](https://supabase.com/docs/guides/platform/read-replicas).

## Auth setup in progress — 2026-10-01

User selected the existing Intake project for SaaS auth, superseding the earlier isolated-project recommendation. Provider settings and OAuth server inspected live. Email login enabled; Google/GitHub disabled. The Vite/Supabase consent page in `saas/auth` is deployed at https://pit.ohlabs.ai on Cloudflare Workers, version `42067db5-c775-4961-b3e5-d906e21442a7`; build and HTTPS navigation checks pass, and the browser renders the email form. With explicit user approval, Site URL and the two fixed callback allowlist entries were saved, OAuth server enabled at `/oauth/consent`, and dynamic registration kept off. OAuth discovery and public auth settings were verified. Actual email login, consent and plugin linking remain untested. Provider configuration, tenant storage policies and hosted MCP remain unfinished; the consent client allowlist is empty. No existing credentials, keys, corpus schema or policies changed. Native v1 sinks remain an open product-scope decision; tool/API writes do not depend on source adapters.

## Hosted MCP implementation — 2026-10-01

SaaS tenant storage and reader RPCs applied to Intake; personal storage unchanged. Worker deployed at `/mcp` with discovery and strict JWT validation. Approved Codex public PKCE client is registered and enabled; actual login reached the deployed sign-in page, awaiting user email login. Local and live rollback-only isolation tests pass. Token exchange, custom-audience Data API acceptance and authenticated remote tools remain unverified. See [implementation and evidence](saas/README.md).

## First hosted save/recover journey verified — 2026-10-01

User completed email login and OAuth consent; native Codex confirmed login. All hosted tools verified through saved OAuth credentials: append, duplicate receipt preservation, literal search, exact Unicode range and enumeration. Global `pit_hosted` connection is configured with registered callback pinned. Custom-audience tokens are accepted by the Data API under tenant/client RLS. Production ChatGPT client linking and directory publication remain outstanding.
