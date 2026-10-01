# The Pit

The Pit is an append-only corpus of distinct unstructured text, with an open read interface so agents can build their own search tools and run searches and transforms close to the data. Identical text is stored once; repeated submissions are ignored.

## Core invariant: the source is irrelevant

> The moment you start caring about what the source is, you are doing something wrong.

This applies to the Pit's core storage and interfaces. Text is text. Its origin does not determine whether it can be stored, how it is represented, or which operations are available on it. We do not need to know whether it came from a conversation, an email, a repository, or anything else.

Capture preserves the text received. It does not classify, normalize, extract entities, impose a document model, or require a semantic projection. Source-specific interpretation belongs to readers that choose to perform it.

Sinks write text directly to a table. **Do not enforce an application-specific 50 MB limit.** The user removed that requirement when deciding the schema; 50 MB remains a planning reference. Database and transport limits still apply. Preserve accepted text without silent truncation or content interpretation.

**Expected workload:** The user estimates that 99% of entries will be under 1 MB (1,000,000 UTF-8 bytes). This is a planning assumption, not a measured distribution. Optimize ordinary reads and writes for that common case.

Storage bookkeeping such as identifiers, positions, lengths, checksums, and commit state can support reliable operation. It must not become a schema for what the text means.

## Agreed behavior

- Append distinct unstructured text and preserve existing entries; ignore identical repeat submissions.
- Read original text, including ranges, and follow new appends.
- Keep direct reading and replay available so agents can build independent retrieval tools.
- Support fast retrieval and searches and transforms close to the data.
- Allow readers to build their own indexes, extractions, and transformations. Those artifacts are replaceable and do not define the authoritative content.
- Run as an always-on service.

The architectural analogy is Google Search: a preserved corpus, indexes and computation over it, and efficient retrieval. It is an analogy, not a decision to use Google's particular products or reproduce its infrastructure.

## Capture and readers

External mirrors can deliver text using services such as Make or Zapier. Their source-specific work stays outside the Pit. Choosing a source or building a custom adapter is not a prerequisite for designing the core.

A full-text index can be one reader. An agent's custom search program can be another. The read interface must remain open beyond any built-in search API. Indexing or interpretation must not be a condition of accepting text.

The first [retrieval trial](retrieval.md) returns bounded original passages with immutable entry/range anchors. Literal search and bounded range retrieval now execute in PostgreSQL before transfer, using a reader-owned trigram GIN index.

Preservation means the text actually received by the Pit. An external mirror may already have changed what its source supplied.

## Decisions still open

- A reliable commit-ordered follow/replay interface beyond ordinary table reads.
- The deployment layout and how computation runs close to storage.
- Any initial search implementation and its measured performance.

**Preferred v1 platform: Supabase PostgreSQL.** The user identifies Supabase as personally the least hassle. Project `iunbpyiylsbkscjaisid` and table `entries` are live. The generated SHA-256 ID, receipt default, content-only inserts, exact readback, duplicate handling, and restricted read/append access have been verified. Workload performance remains unmeasured. See the [table contract](schema.md): `id`, `received_at`, and `content`, with direct inserts and no size check.

**Agreed uniqueness:** `id` is the database-computed SHA-256 of the exact text, allowing sinks to use `ON CONFLICT (id) DO NOTHING`. Identical text is stored once and keeps its first stored receipt time. The user explicitly does not want repeat occurrences retained. No normalization or source-dependent identity is involved.

Bigtable, BigQuery, Splunk, ClickHouse, and other approaches remain comparison history. The multi-service GCS/Hyperdisk/Cloud SQL/Compute Engine/Tantivy recommendation was withdrawn. See the [implementation note](implementation-recommendation.md) and [managed hosting comparison](managed-options.md) for rationale and remaining implementation questions.

## Context and tracking

The user selected an on-demand **Export to Pit** plugin for ChatGPT Work and accepts overlapping session snapshots. See the [installed plugin and verified connection](plugin.md). Version 0.5.0 is installed and enabled locally; export to Supabase and exact readback succeeded for this session. The user authorized a global PreCompact hook for all supported local sessions. Work runtime discovery and exact-definition trust are verified; the first natural compaction after restarting the harness remains the automatic-trigger check. Cloud remains out of scope.

See [the framing session](problem-weave.md) for the Aim and the independent problem-weave synthesis: distinct problems, dependencies, tensions, candidate tactics, and the boundary for choosing solutions.

The session now includes a [solution-space recommendation](problem-weave.md#solution-space) and [dissent review](problem-weave.md#dissent). The recommended next proof is a durable text history with independent nearby readers. This is an analysis recommendation; specific storage products, execution facilities, and production commitments remain open.

Established in conversation on 2026-09-30. The earlier [shared conversation](https://chatgpt.com/share/6abcd247-cdd8-83eb-9658-5dcbace22125) provides background; the invariant above records the user's explicit clarification here.

The earlier `durch/intake` project is cautionary prior work: its structure and projections illustrate the failure to avoid. Its data model is not a starting point for the Pit.

Keep confirmed decisions and open proposals distinct as this folder grows. Record concrete decisions and their reasons here or in linked notes. Update this brief when a decision is actually made.

## Choosing retrieval

The local plugin now advertises missing-context retrieval, exposes direct pit_search and pit_read_range tools, and reminds the model that precompaction text remains available. Compaction summaries are trusted; retrieval happens only for specific missing context, without routine pointer injection or hydration. A fresh native model trial autonomously searched and expanded a range; a separate native compaction trial recovered a pointer never present in model history. See [execution and verification](retrieval-adoption.md). Cloud remains out of scope. Existing running harnesses may need a restart to load the updated tools and hooks.
