# Ranked query reader

Status: proposed additive reader, delivered as a PR. No production migration or Worker deployment is performed by this change.

## Aim and boundary

Let a model or deterministic caller submit a few useful keywords and receive a small ranked set of original passages with exact, expandable citations. Filtering and scoring execute beside the corpus; there is no model call in `pit_query`. The answering model can spend its context on evidence instead of whole transcripts.

Pit still accepts and preserves arbitrary unstructured text. This reader does not parse conversations, classify entries, or require source metadata. Entry identity and receipt time are the only stored scope used here. A reader that knows source/session/project membership can supply entry IDs. Do not infer project scope from directory names and silently exclude material. Receipt time is not the time of events described in the text.

## Contract

The local and hosted MCP tool is `pit_query`. Personal SQL is `public.pit_query`; hosted SQL is `public.pit_saas_query`.

```json
{"terms":["deployment","access"],"limit":5}
```

Optional `entry_ids` restricts to exact immutable hashes; an empty list selects nothing. Optional `since` (inclusive) and `until` (exclusive) restrict receipt timestamps. Timestamps require a timezone at the MCP boundary. Scope is never broadened after an empty result.

Supply 1–16 nonblank literal terms, each at most 100 Unicode code points, and a result limit of 1–20. Terms are case-insensitive, not regexes, stemming, synonyms or an embedded natural-language question parser. A caller can use a model to extract terms from a question, but that happens outside Pit. Each candidate entry must contain every term; individual returned windows may contain fewer and are ranked first by distinct term coverage, then PostgreSQL cover-density rank over the `simple` text-search configuration. This ranking is lexical, not BM25 or semantic similarity; ties use receipt time, entry hash and original offset. Case handling follows the database collation.

Results retain `id`, `received_at`, `start_char`, `end_char`, `excerpt` `score` (distinct term count) and `lexical_rank`. Offsets are zero-based Unicode code points, with an exclusive end. Expand via the existing `pit_read_range`. Excerpts are slices of preserved text, not generated headlines. Exact duplicate windows are collapsed before scoring. When a candidate is an exact prefix of another candidate within the scan budget, the longer candidate supplies the evidence. This avoids repeatedly scoring shared text; shifted or other near-duplicate snapshots are not claimed to be deduplicated.

## Bounded retrieval and honest coverage

The reader examines the newest 100 matching entries and scores overlapping windows of up to 1,800 characters, stepping by 1,400 characters. It examines at most the first 1,000,000 characters of each candidate. These are reader limits, never capture limits. The response reports `candidates_truncated` and `characters_truncated` under `coverage`; either means other relevant evidence may have been omitted. A short result list or empty result is not proof of absence, especially when coverage is incomplete.

The bounds limit window scoring and response size, not total database work to locate candidate entries. Existing trigram search can assist literal predicates; very short/common terms and large corpora still require measurement. No constant-time or production latency guarantee is implied. Use the existing paged literal reader and range reader for further exploration, or narrow to known entry IDs or a receipt interval. This API is deliberately not an exhaustive analytical query interface.

## Installation and rollback

Personal deployment: apply `query.sql` after the existing personal table and reader permissions are installed. Hosted deployment: apply `saas/query.sql` after `saas/tenant-storage.sql`. Review the target database first; do not apply disposable test bootstrap to a live database. Expose the corresponding updated MCP implementation only after its SQL exists. The hosted Worker forwards the caller token; its query runs as the caller under existing row-level security, with no service-role bypass.

Both scripts are additive reader functions. Existing append, literal search, search pagination, range and direct reads are preserved. Rollback can remove the new MCP tool and drop the new query functions; no corpus migration or data rollback is needed.

## Execution checks

The acceptance checks target the shortcuts most likely to give plausible but wrong retrieval: a first-match-only implementation misses later useful windows; generated excerpts break original offsets; global ranking before tenant filtering leaks another account; silent scope fallback returns unrelated evidence; duplicate snapshots crowd out distinct results; silent scan caps misrepresent absence. SQL and MCP tests cover these boundaries with synthetic text, without committing private corpus material.

The earlier Ether retrieval experiment motivated this API but does not establish this ranking rule's accuracy or latency. Its excerpt-level PostgreSQL conjunction and Leviathan BM25 results used a different corpus preparation and ranking implementation. See the measured sample results below. Production-scale evaluation and caller adoption remain separate from this PR.

## Reproducible contract tests

The `Reader contracts` workflow creates a disposable PostgreSQL 16 service and runs the local Python suite, SQL contracts, hosted MCP tests/build and package verification. To reproduce the database checks in a disposable cluster with a superuser connection:

```sh
psql -v ON_ERROR_STOP=1 -f saas/tests/bootstrap.sql -f saas/tenant-storage.sql -f query.sql -f saas/query.sql -f saas/tests/query.sql -f saas/search-pagination.sql -f saas/tests/search-pagination.sql
```

The bootstrap creates test roles and auth helpers; it is not a production setup script. Test fixtures roll back. No live credentials are needed.

## Sample measurement — 2026-10-05

A private, previously prepared 300-entry sample was copied into disposable PostgreSQL 16 for evaluation. After exact-text deduplication of the prepared copies, it contained 275 distinct entries. The six existing keyword cases were reused, so this is a development regression sample, not a held-out quality estimate. No private text or credentials are included in this PR. The source corpus was unchanged, and the evaluation transaction rolled back.

| Case | Target evidence in top five | Median database time, three calls |
| --- | --- | --- |
| Hub deployment | Yes | 1,163 ms |
| Touch wiring | Yes | 1,230 ms |
| Systemd ordering | Yes | 1,495 ms |
| NAA portability | Yes | 1,241 ms |
| Scanner lyrics | Yes | 492 ms |
| Direct MCP controls | Yes | 1,883 ms |

All 30 returned citation ranges were independently sliced from their stored originals and matched exactly. Hub correctly reported candidate truncation; none of these queries hit the final character cap. Times exclude transport and installation/index setup and are not a production latency guarantee. The first keyword-coverage-only implementation found three of six targets; lexical ranking, a larger per-entry budget and exact-prefix reuse produced the final result. This does not establish general natural-language or semantic retrieval quality.

Verification: 82 Python tests, seven hosted Worker tests, TypeScript/frontend build, portable package validation, and disposable SQL assertions covering Unicode, literal injection-like terms, scope, receipt bounds, prefix reuse, scan caps, two-tenant isolation and anonymous denial. Production deployment, wider-corpus latency and adoption by Ether readers remain outside this PR.
