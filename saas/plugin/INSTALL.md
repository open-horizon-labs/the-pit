# Try The Pit in ChatGPT Work

The hosted service is running at https://pit.ohlabs.ai. You use your own Pit account and private text. You do not need to deploy the service or obtain database credentials.

This is a developer trial, not a public directory installation. The current ZIP references the author's unpublished ChatGPT integration. Installation by a different ChatGPT account has not yet been verified. Follow the first path before creating a separate connection.

2026-10-02 inspection: the author's ChatGPT integration is marked `DEVELOPMENT`. Its visible actions offered Manage, ZIP download, version upload and deletion, but no sharing control. This does not establish whether another account can resolve its ID; the recipient installation below is the test.

## First: try the supplied package

1. Use ChatGPT Work with local execution and access to the Plugins Directory. Developer mode and installation availability depend on your plan and workspace policy.
2. Obtain `the-pit-hosted-0.1.1.zip` from the publisher. In the Plugins Directory, use its archive import control if available, select the ZIP, then install The Pit. If archive import is unavailable, ask Work to install the plugin folder from a local marketplace using the instructions at https://developers.openai.com/plugins/build/plugins . The package folder is `saas/plugin` in this repository.
3. Open The Pit's app connection and choose Connect. Sign in using your own email; complete the email link in the same browser profile that started sign-in. The email sign-in flow can create your account when registrations are enabled. If registration fails, report the visible error to the publisher rather than using somebody else's credentials.
4. Review and approve the connection to your private Pit.
5. In a new Work conversation, enable The Pit and run the checks below.

If the app is inaccessible, missing, or cannot be connected, send the publisher the visible error and your ChatGPT surface/workspace type. Importing the skills alone is not a working Pit connection.

## Fallback: create your own developer connection

This path needs one operator setup step. It uses the existing service and public OAuth client; a new OAuth client is not required for every user.

1. In ChatGPT Settings → Security and login, enable Developer mode if available.
2. Open https://chatgpt.com/plugins and choose the plus/create control. Name the connection The Pit and use MCP URL `https://pit.ohlabs.ai/mcp`.
3. Choose OAuth with a predefined/user-supplied public client if offered. Client ID: `79c0b4f7-d42d-47f2-9a65-2cfb38f16ab4`. Token endpoint authentication: `none`; no client secret. Use the discovered authorization/token endpoints. Avoid requesting OIDC identity scopes; the currently configured connection uses `offline_access`.
4. Copy the **exact OAuth callback URI** ChatGPT displays. Send that URI to the publisher before attempting authorization. It must be added to the existing client's exact redirect list; `invalid redirect_uri` means this step is incomplete. No wildcard redirects are needed.
5. After the publisher confirms registration, complete connection creation, sign in to your own Pit account and approve consent.
6. Send the connection's technical ID from its ChatGPT URL (`plugin_asdk_app_…`) to the publisher. These are public configuration identifiers; do not send passwords, magic links, authorization codes or tokens.
7. The publisher supplies a recipient package that maps `.app.json` to your connection. Install it and run the checks below.

The exact UI labels may differ. If ChatGPT does not offer predefined public-client configuration, stop and send the visible screen/error; do not substitute another auth method.

## Verify the connection

Use harmless text unique to you:

1. `Save this exact text to my Pit: My Pit trial — violet kite.` Expect a verified append receipt with a hash.
2. Start a new conversation: `Find "violet kite" in my Pit.` Expect an excerpt of the saved text.
3. `Read characters 0 through 20 of that entry.` Expect the exact range [0,20), not the whole corpus.
4. Save the identical text again. Expect the same hash and original receipt, with `inserted=false` and `verified=true`.
5. Visit https://pit.ohlabs.ai signed into the same account and export your text. Confirm it contains your sample.

Do not interpret a failed search as an empty corpus. Record the error and the append receipt. Your first Pit should not contain the publisher's trial text; report unexpected entries before saving private material.

## Publisher setup for the fallback

- Inspect the supplied callback; require the real ChatGPT HTTPS callback, not an arbitrary destination. Confirm the security-sensitive access change at action time before applying it through browser controls.
- In Intake → Authentication → OAuth clients, edit The Pit (`79c0b4f7-d42d-47f2-9a65-2cfb38f16ab4`). Add the supplied complete callback to its redirect list **while preserving existing redirects**. Keep public client / token authentication `none` / PKCE. Existing client allowlists already cover this client ID; changing a redirect does not require a new allowlist entry.
- In a separate local copy of the package, change only `.app.json` → `apps.pit.id` to the recipient's `asdk_app_…` technical ID (strip the leading `plugin_` from the URL ID). Keep the endpoint and both skills. ZIP the package contents with `plugin.json` at the archive root. Do not overwrite the author's package mapping or include local credentials, environment files or capture hooks.
- Verify recipient installation and all checks before describing this as independently usable. Record which package mapping and callback were tested.

Official setup references: https://developers.openai.com/plugins/deploy/connect-chatgpt and https://developers.openai.com/plugins/build/plugins .
