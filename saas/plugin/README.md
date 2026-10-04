# Hosted plugin prototype

For another developer's installation trial, follow [INSTALL.md](INSTALL.md). It covers trying the current package first, the operator-assisted fallback if the unpublished integration is inaccessible, and concrete save/retrieve checks. Cross-account installation remains unverified. The historical notes below describe the author's successful trial.

Portable Agent Plugins package, version 0.1.0. Remote endpoint: `https://pit.ohlabs.ai/mcp`. Save and retrieval skills validated with the Skill Creator validator. No credentials, local capture scripts or lifecycle hooks are bundled.

This is an authoring prototype, not a published directory listing. Public submission still needs complete publisher/legal metadata and real installed-client evaluation.

2026-10-01: ChatGPT Personal plugin creation discovered the existing OAuth endpoints and offered a user-defined public client with token endpoint auth method `none`. The exact callback displayed for this pending connection is `https://chatgpt.com/connector/oauth/4J_YISRQDScM`. DCR and CIMD remain unavailable. User approved registration and connection. Public client `79c0b4f7-d42d-47f2-9a65-2cfb38f16ab4`, named The Pit, was created with that exact redirect. Database allowlist insertion was verified live. Worker and consent UI allowlists are prepared but deployment failed because Wrangler was signed into the Izun account rather than the owning Slon u sobi account. ChatGPT creation and end-to-end calls remain pending. Confirm the displayed callback again before registration if recreating the dialog.

The existing Codex OAuth client remains separate. After ChatGPT connects, retain its technical `plugin_asdk_app...` ID and use the documented OpenAI registered-app mapping for Work installation if needed. Do not guess that ID or claim the portable remote configuration is already a tested Work install.

2026-10-01 follow-up: Worker and consent allowlists deployed successfully as version `265afab3-a61b-42aa-8544-75ff5a62efc0`. ChatGPT Personal plugin `plugin_asdk_app_6abe8a8a55788191887eef2d75091666` connected through the exact callback; consent requested only `offline_access`, with OIDC disabled. Registered-app mapping uses `asdk_app_6abe8a8a55788191887eef2d75091666` as in official OpenAI package examples. The portable package is not yet installed/evaluated as a complete skill bundle.

Actual browser Work append trial returned inserted=true and verified=true for `Pit Work trial 2026-10-01 — amber fox.` Hash `08301689000f495b994e07e72b08ed612d5d906cbd7d747c36a6e86c5b046f8b`, receipt `2026-10-01T16:31:44.79145+00:00`. Trial chat: https://chatgpt.com/c/6abe8acf-6674-83ed-ad5b-1f057b34a2cf. One synthetic entry remains.

Separate browser Work session searched the literal trial phrase and read range [0,38), returning exact text and the same hash. Retrieval chat: https://chatgpt.com/c/6abe8b2f-6eb4-83eb-a0e1-e4a8e1e3a3b5. This verifies the hosted MCP workflow across sessions; it does not yet verify the packaged skills.

Archive import and installation succeeded. Personal bundle `Plugin_a7990534984c819180e58c6840a8bd10` displays version 0.1.0, both skills and one app marked Connected. Bundle workflow evaluation chat: https://chatgpt.com/c/6abe8bf4-9d1c-83eb-ab79-535665e9fa03 (passed).

Installed bundle evaluation passed: Work reported using retrieve-from-pit with bounded search/read [0,38), then save-to-pit with the exact recovered text. Append receipt inserted=false, verified=true, same immutable hash. UI activity included Reading Pit Storage Skills. No second entry was added. This is one positive evaluation, not broad activation/negative-case coverage.
