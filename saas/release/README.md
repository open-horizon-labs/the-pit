# Public release preparation

This is a release checklist, not publication evidence.

## Current status — 2026-10-01

- Production storage allowance and erasure migrations applied; rollback-only lifecycle/isolation tests passed, existing entries preserved.
- User-selected defaults: initial 1 GiB allowance per account, retain saved text until erasure. Endpoint throttle already deployed.
- Account website erasure control enabled. Static privacy, terms and support published under Open Horizon Labs, pit@urch.eu. Provider backups and shared sign-in identity are distinguished from live-corpus erasure.
- Worker/site deployed as `eb031322-58b7-4ee4-a3e5-76e6face306d`; hosted search/range/duplicate append live-verified.
- Package 0.1.1 prepared with listing, icons, policy URLs and eight test definitions. Reviewer case execution/video, remaining browser lifecycle journeys and portal submission still pending.
- Reviewer account `pit+review@urch.eu` created by the user, UUID `2788e1bb-8024-461c-bcd2-fbbdd4d24f87`. User completed sign-in in an isolated private Arc window; password remains outside agent context.
- Reviewer browser export verified: empty corpus produced a zero-byte NDJSON file; owner-role append RPC then saved exact text `The launch color is amber. 🌕`, hash `125afc02c6c124f1fc37ae97767a747a4f8663107e8c41671cba412ea7e94321`. Subsequent browser export contained exactly that one entry with original Unicode. This verifies export, not reviewer MCP model cases.
- Native Arc control works; browser extension is unresponsive and CLI Supabase is unauthenticated. Never infer tests passed from definitions or SQL-only verification.
- Browser erasure journey passed after explicit user approval: reviewer account confirmation dialog accepted, website reported one entry erased, subsequent NDJSON export was empty. Reviewer remained signed in. No personal corpus or shared identity was targeted.
- Public portal upload blocked: current organization is Slon u sobi, individual verification shows Approved under organization settings, but `/plugins` still requires developer identity verification after a fresh navigation/retry. Business verification remains unstarted. No package uploaded and no identity/legal claims submitted. Resolve publisher verification before submission; do not infer Open Horizon Labs is verified from the current organization label.
- 2026-10-02 update: user completed verification and explicitly selected Personal for submission. Live Personal settings show Individual Approved, organization `org-6ZBY4wyKTpl7F1jTP1EUSlm9`, project `proj_zG2J3T2aU1dw3kPS7mhm7ZzD`. Personal `/plugins` upload still displays the developer identity prerequisite. No ZIP uploaded. Similar primary reports and OpenAI Support response: https://community.openai.com/t/plugin-submission-blocked-despite-approved-individual-verification/1391411 . This is evidence of a possible portal synchronization problem, not proof of this account's backend cause. Do not repeat identity verification or change to Slon u sobi as a workaround without user direction. Directory publisher must use the selected verified personal identity; existing Open Horizon Labs branding does not establish business verification.

The historical preparation and checklist below are superseded where marked above.

## Implemented locally

- Explicit read/write/destructive/open-world tool annotations.
- Hosted endpoint per-user throttle: 120 requests / 60 seconds in each Cloudflare location. Approximate local counters, not a global cost ceiling; counts MCP protocol requests as well as operations. Direct Data API is outside this throttle.
- Account export: keyset pages of original entries, serialized as NDJSON in the browser. Export is a snapshot scan, not a consistent point-in-time snapshot; large exports consume browser memory. New concurrent entries may require another export. Downloaded files are the user's responsibility.
- Password sign-in alternative for dedicated reviewer accounts; passwords go directly through Supabase Auth and are not logged. Reviewer creation is still pending.
- Information pages explicitly marked draft. Publisher confirmed: Open Horizon Labs; support/privacy contact: pit@urch.eu. Retention and terms decisions must be finalized before publication.
- Proposed database storage allowance in `../storage-allowance.sql`: 1 GiB per account; no entry cap, text interpretation or normalization. Administrator-adjustable; concurrency-safe per-account accounting, direct inserts included, duplicates free. Local tests only until applied.
- Icon and review cases prepared. Cases have not been run using a reviewer account.

## Before submitting

1. Publisher and contact confirmed by user: Open Horizon Labs, pit@urch.eu. Complete platform identity verification; finalize retention timeline, jurisdiction and account-erasure process. Finalize policies; do not submit draft URLs as final policies.
2. Inspect production schema, apply allowance migration and verify existing accounts and concurrent writes. Confirm allowance before advertising it.
3. Inspect/apply `../account-erasure.sql`, then enable `VITE_PIT_ACCOUNT_ERASURE=enabled` and exercise the confirmation journey. Prepared RPC permits direct account sessions only, denies OAuth clients and erases own SaaS corpus. Local isolation tests pass. It is not production-applied; support and account closure remain unfinished. Intake Auth is shared: do not delete `auth.users` to erase a Pit account without checking other applications. Existing personal `entries` is separate and must not be erased implicitly.
4. Test fresh registration, consent denial, token expiry/refresh, browser export and password login. Configure production email delivery as necessary; email delivery is not proven by local builds.
5. Create a dedicated reviewer account with password and sample data, not personal data. Keep credentials outside package/chat. Run five positive and three negative cases; record walkthrough.
6. Add final `supportURL`, `privacyPolicyURL`, `termsOfServiceURL`, long listing description, release notes and video URL. Register/verify publisher identity and MCP hostname through the submission portal.
7. Upload ZIP, resolve automated metadata/skill/tool findings, submit for review. Publish only after approval and user authorization.

## Sources

- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/plugin-guidelines
- https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/

Reviewed 2026-10-01. Reviewers require access without email codes/magic links. Hosted tools must operate on explicitly supplied text rather than reconstruct chat logs. Public plugin descriptions cannot promote subscription purchases.
