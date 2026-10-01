# Pit account and consent page

Deployed at https://pit.ohlabs.ai on 2026-10-01. Email sign-in, consent and Codex hosted linking are end-to-end verified; production ChatGPT linking is pending. Target project: Intake (`iunbpyiylsbkscjaisid`), selected by the user on 2026-10-01.

Install dependencies with `npm ci`, copy `.env.example` to `.env.local`, supply the project URL and **publishable** key, then `npm run dev -- --port 3000` or `npm run build`. Never use a secret/service-role key here. The static host must serve index.html for `/oauth/consent` and `/auth/callback`. Environment values are included in the public bundle.

Routes: sign-in with email magic link; optional Google/GitHub buttons once their Supabase providers are configured; PKCE callback; explicit OAuth consent or denial using Supabase's SDK. The authorization ID survives login through a fixed callback query parameter. User-supplied return URLs are never followed. Remote client metadata is rendered as text, not HTML. No remote client logos or arbitrary web links are loaded.

`VITE_PIT_CLIENT_IDS` is a temporary consent-UI allowlist. It is **not backend authorization**. Unknown clients cannot be approved through this UI. Before adding any client, implement and verify its database/MCP access policy; replace the generic permission text with its actual permitted read/append operations. Existing consent returned by Supabase remains governed by Supabase and server policies.

## Live configuration inspected

- Email login enabled, new signup allowed, email confirmation enabled.
- Google and GitHub disabled; no provider secrets read or changed.
- OAuth server enabled with user approval, authorization path `/oauth/consent`, dynamic app registration off.
- Site URL `https://pit.ohlabs.ai`.
- Redirect allowlist: `https://pit.ohlabs.ai/auth/callback` and `https://pit.ohlabs.ai/auth/callback?authorization_id=*`. The prior allowlist was empty.
- Public auth settings accept the deployed publishable key; OAuth discovery returns the expected Intake issuer, authorization/token endpoints and PKCE support.

## Remaining setup

Email sign-in, consent and hosted Codex tool calls are verified. The project exposes an ES256 signing key; no key rotation was needed. Tenant storage and hosted MCP are implemented separately from this page.

1. Verify a fresh login using the saved fixed Codex callback configuration, plus refresh/expiry and consent denial/error journeys.
2. Register the production ChatGPT client using the exact callback shown in its management page, then verify the complete ChatGPT journey. Keep dynamic registration off unless explicitly authorized.
3. Verify SMTP delivery/rate limits for public rollout. Social providers are optional and still disabled.
4. Complete public product lifecycle, quotas and directory packaging before launch.

The OAuth feature is currently beta per official docs. Reference: https://supabase.com/docs/guides/auth/oauth-server/getting-started

## Cloudflare Worker

User selected `pit.ohlabs.ai`. `wrangler.jsonc` uses Workers Static Assets with SPA fallback for consent and callback routes. `npm run deploy` builds with a guard requiring Intake's public project URL and a browser-safe `sb_publishable_` key; missing configuration cannot silently ship an inactive login page. No secret keys belong in the frontend. Deployment succeeded; current Worker version is `e30b1201-5326-491e-9d0b-a001f96ab895`. HTTPS navigation to root, consent and callback routes returns 200; the native browser renders the email sign-in form. Email sign-in and Codex OAuth linking subsequently passed.

Production Supabase setup: Site URL `https://pit.ohlabs.ai`, Authorization Path `/oauth/consent`, and exact redirects `https://pit.ohlabs.ai/auth/callback` plus `https://pit.ohlabs.ai/auth/callback?authorization_id=*` for the SDK callback query. The wildcard is restricted to the authorization ID on the fixed HTTPS callback path; verify its matching in the real flow. Preserve existing redirect allowlist entries until verified unnecessary.

Cloudflare deployment uses the verified Slon u sobi account `f048f3132be36fa1aaa8611992002b3f`, pinned in `wrangler.jsonc`. The custom domain is live. No provider secrets or existing signing keys were changed. The approved Codex client is now allowlisted; tenant policies and hosted MCP are implemented. Actual token exchange and authenticated hosted tool calls pass. See ../README.md for current implementation evidence.
