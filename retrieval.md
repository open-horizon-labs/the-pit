# Reading passages from The Pit

## Live read-only trial

The user asked for queries against the corpus and suggested returning a surrounding range by default rather than an entire matching session. The [reader probe](reader_probe.py) ran three literal, case-insensitive searches through the existing authenticated Data API:

| Query | Recovered passage | Returned entries |
|---|---|---|
| `moment you start caring` | The user's source-indifference invariant | 2 |
| `on conflict` | The exact-text hash/deduplication discussion | 2 |
| `5MB` | The earlier size-cap comparison | 2 |

The two entries are overlapping snapshots. Identical excerpt text was collapsed only in the reader output, with both immutable entry/range anchors retained. No source identification, conversation identity, or changes to stored text were needed.

The probe returned 2,294 UTF-8 bytes of excerpt text across three distinct passages. It fetched two full entries totaling 137,415 content bytes into the local Python process, cached them during the trial, and exposed only the bounded excerpts to model context. **This is not database-side range retrieval.** The first query including reads took approximately 619 ms; the remaining metadata searches plus cached slicing took 132 and 139 ms. Two entries and three queries provide no scale/performance evidence.

Example stable anchor: entry `44ab88426e5e702016555f805e8c29aa1e578adad65379be99b9ab50f70a565e`, characters `[30386, 30979)`, contains the source-indifference statement.

## Proposed reader interface

Make passage retrieval the normal read path:

- `search(query, limit, context)` returns an entry ID, match location, surrounding original text, and returned range bounds. Start with roughly 1,000 characters per passage and a small overall result budget. This is a reader default, not a storage limit.
- `read_range(id, start, end)` returns the exact requested slice for expansion or continuation, plus its bounds and entry length. Full-entry reads remain available explicitly.
- Use zero-based, half-open Unicode code-point offsets: `[start, end)`. These are Python string positions, not UTF-8 byte offsets or JavaScript UTF-16 positions. Convert `start` to `start + 1` for PostgreSQL substring; count is `end - start`.
- Grow the window or follow adjacent ranges when the excerpt lacks enough context. Retrieval ranking, window selection, and identical-excerpt grouping belong to independent readers.

A small PostgreSQL `SECURITY INVOKER` function exposed through the Data API can perform matching and `substring(content, start + 1, end - start)` **before network transfer**, under the caller's existing `entries` permissions and RLS. Search functions should emit original slices rather than modified/highlighted text so their returned offsets remain meaningful. Restrict function execution deliberately and reserve administrator privileges for deployment. No raw arbitrary-SQL execution endpoint is necessary for this first reader.

This function would avoid transferring whole matches. It would not make finding every match fast automatically: literal substring search initially scans text. Index choice and large-corpus measurements are separate reader work. Neither substring extraction nor an index requires changing the authoritative `entries` schema.

The first candidate for the current literal `ILIKE` queries is a GIN `pg_trgm` index on `content`. PostgreSQL supports indexed substring/regular-expression queries with this operator class. Indexes remain replaceable reader infrastructure. This candidate has not been applied or performance-tested. See [PostgreSQL trigram index support](https://www.postgresql.org/docs/current/pgtrgm.html#PGTRGM-INDEX).

**Status:** the live probe is implemented; database-side search/snippet and range functions are proposed and have not been deployed. The current plugin's explicit full-entry read remains unchanged.

References: [PostgreSQL string functions](https://www.postgresql.org/docs/current/functions-string.html), [Supabase database functions](https://supabase.com/docs/guides/database/functions).

## Deployed database readers — 2026-10-01

Applied readers.sql to Supabase project iunbpyiylsbkscjaisid, PostgreSQL 17.6. The entries schema is unchanged. Reader-owned pg_trgm and entries_content_trgm_idx provide GIN acceleration for literal case-insensitive matching.

pit_search(query, limit=5, context=500) returns the first match per entry, newest first, with original-text excerpts and immutable hash/range anchors. Limits: query 1–1000 characters, 1–20 entries, context 0–2000 on each side. No ranking or occurrence pagination yet. PostgreSQL literal regex director ***= prevents user punctuation from becoming regex syntax; predicate and offsets use identical case rules.

pit_read_range(id, start=0, end=1000) returns at most 20,000 original characters. Offsets are zero-based Unicode code points, half-open [start,end). Bounds past EOF clamp; absent/inaccessible entries return an empty list. Full reads remain explicitly available.

Both functions are SECURITY INVOKER with empty search_path, no PUBLIC/anon execution, authenticated execution, and existing entries RLS. Migration and permissions were applied atomically. No canonical content projections or source metadata were added.

Live authenticated checks verified exact snippets, lengths and follow-up ranges against privately fetched originals for three trial phrases and literal parentheses, percent, underscore and backslash. Anonymous RPC and invalid parameters were denied. The three phrase searches returned 1,282 UTF-8 excerpt bytes across six matches; normal retrieval fetched no full entries. Full originals were fetched privately only for verification.

Installed plugin 0.4.0 exposes --search and --range; reader_probe.py now uses database excerpts exclusively. Corpus-scale latency remains unmeasured. Short queries with no extractable trigrams can scan; an index does not guarantee every query is cheap.

Database catalog verification: index_valid=true; both functions security_invoker=true, anon_execute=false, authenticated_execute=true. Unicode literal offset test on Č followed by an emoji and C++ returned start=2. All 22 local tests passed.
