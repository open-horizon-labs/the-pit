# Make shared Pit sink — live 2026-10-01

[The Pit — Append text](https://eu2.make.com/385368/scenarios/9897447/edit) is active and on-demand in Slon u sobi d.o.o. / My Team. No polling schedule or external mirror has been configured.

## Interface

- Required input: `content` (multiline text), preserved exactly.
- Output: `inserted` (boolean). True for new text; false for an exact duplicate. Both outcomes succeed.
- Flow: Start scenario → PostgreSQL Execute a function → Return output.
- Function: `public.pit_append_text(text)`. Make parameter key `@01:text` maps to `{{1.content}}`; return output maps `{{2.pit_append_text}}` to inserted.
- Connection ID: 14636456. Dedicated `pit_make_sink` account, session pooler, database postgres. Credentials entered by user in Make; not stored in this repository.

The role can execute the append function but has no direct table or column privileges on entries. Function is SECURITY DEFINER, fixed empty search_path, fully qualified table, exact INSERT ... ON CONFLICT DO NOTHING. Execution is denied to PUBLIC, anon, authenticated and service_role. Reader/plugin policies unchanged.

## Verification

Owner-side transaction test passed Unicode/quotes/whitespace preservation and duplicate suppression; test writes rolled back. Catalog assertions checked role execution, absence of direct table/column rights (including TRUNCATE/MAINTAIN), and absence of public client function execution.

Live Make runs:

- fc862e8e0b84492f8e7f813d36941110: success, PostgreSQL returned pit_append_text=true. Pit readback matched test text byte-for-byte.
- a41e93cc43a449429693e2293e080c0a: same input, success, declared output inserted=false. Readback verified one exact row and unchanged original received_at.
- Test entry hash: 62d1be8e3d4ed2bbccd73bbe8cfef38248318e53be73c600d8bdc4d4252f01e4; first receipt 2026-10-01T08:56:43.660699+00:00. One small diagnostic entry remains in the append-only corpus.

Final scenario readback confirms active, on-demand, healthy connection, required content input, boolean inserted output and no incomplete executions. This is an end-to-end sink test, not a test of any external trigger.

## Add a mirror

In another Make scenario, configure its trigger and compose the text to preserve. Add Scenarios → Call a scenario, select The Pit — Append text, and map the text into content. An exact duplicate returns inserted=false without failure; do not interpret that as a missing delivery. Mapping is outside the Pit; no source metadata is required by the core.

## Boundaries

This role has access only to the append operation; it cannot recover existing content. No automatic source collection is enabled yet. The earlier native Supabase credential request remains unused because it requires a broad project secret key.
