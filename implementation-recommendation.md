# Concrete implementation recommendation

Date: 2026-09-30. Status: Supabase PostgreSQL is the preferred v1 platform following the user's developer-experience preference. Not provisioned or implemented. The earlier multi-service stack is withdrawn. The invariant in README/AGENTS remains authoritative.

## Current direction

The user identifies Supabase as personally the least hassle. Start the v1 design with Supabase PostgreSQL: preserve received text with minimal operational bookkeeping, append-only writes, and open reads. The [developer-experience and SaaS comparison](managed-options.md) supports this preference. A paid plan and project have not been chosen or provisioned. General reader execution remains a separate placement question; a built-in search index must not become the sole read interface.

The candidate analysis below predates that preference. It records trade-offs rather than reopening vendor selection by default.

**Latest schema direction:** Sinks insert directly into one PostgreSQL table; see [schema.md](schema.md). The user explicitly removed enforcement of the 50 MB cap. That figure remains a planning reference, not a database constraint. Earlier cap-based comparisons below are historical rationale.

Exact-text hash uniqueness is now agreed. Use the database-computed SHA-256 as `id` and ignore conflicting inserts, preserving the first stored receipt time. Repeated occurrences are intentionally discarded; the Pit retains distinct text.

**Expected distribution:** The user estimates 99% of entries below 1 MB. Evaluate ordinary read/write performance primarily at that scale, and verify correctness and resource use through 50 MB separately. This is an expected workload, not a benchmark result.

The GCS/Hyperdisk/Cloud SQL/Compute Engine/Tantivy combination below added several services and custom publication/recovery coordination before establishing that an existing engine was insufficient. The user rejected the recommendation. Retain it only as proposal history.

Reopen solution-space option A: an integrated storage/query engine. ClickHouse on SSD-backed storage is a candidate to evaluate, not a user-approved choice. It combines a raw String type, native full-text indexes, SQL, and executable UDFs that stream query blocks through external programs. These features could reduce the custom infrastructure while keeping interpretation in readers. [String](https://clickhouse.com/docs/sql-reference/data-types/string), [full-text search](https://clickhouse.com/blog/full-text-search-ga-release), [UDFs](https://clickhouse.com/docs/sql-reference/functions/udf).

Evaluate memory use and range-read performance for entries up to 50 MB. Also unresolved: acknowledged-append durability and replay ordering, and whether independent readers can build their own indexes from originals without capture changes. Native text search alone does not establish relevance ranking or useful context retrieval. These are reasons to evaluate the engine before recommending it as the Pit. ClickHouse Cloud executable UDFs are currently public beta; managed Cloud and an SSD-backed installation are distinct deployment candidates. [Cloud UDF status](https://clickhouse.com/blog/executable-udfs-clickhouse-cloud-beta), [transaction boundaries](https://clickhouse.com/docs/guides/developer/transactional).

## Effect of the size bound on the shortlist

The 50 MB cap removes a size-driven requirement for object-store indirection or custom physical segmentation. One entry can be one database value with minimal operational bookkeeping and unchanged text. This is an implementation option, not a requirement that readers inherit a content schema.

The assistant's practical shortlist is PostgreSQL and ClickHouse. PostgreSQL is the simpler transactional baseline for preservation and direct reads: its documented 1 GB field limit accommodates the cap. Its native full-text `tsvector` has a separate limit below 1 MB of lexemes and positions, so a single native search vector cannot be assumed to cover every permitted entry. That limit is not a 1 MB limit on stored text. Reader-owned indexing can address this without changing capture. [Field limits](https://www.postgresql.org/docs/current/limits.html), [text-search limits](https://www.postgresql.org/docs/current/textsearch-limitations.html).

ClickHouse remains the first candidate to evaluate against the user's search and nearby-transform priorities, using its native text index and executable UDF facilities. This is not a measured performance win or a vendor commitment. Durability, append ordering, raw access, and independent reader operation remain requirements. A UDF alone does not establish unrestricted reader execution.

Bigtable, BigQuery, Splunk, and a separate object-store/journal design are deprioritized as the initial core, not proven incapable by this size cap. Total corpus size and concurrency still determine operating scale. The estimated 99% below 1 MB is by entry count; the larger tail can contribute substantial bytes and processing cost.

## Withdrawn proposal — retained for history


The remaining sections describe the earlier proposal, not current implementation instructions.

| Responsibility | Recommendation | Scope |
|---|---|---|
| Original text serving copy | Hyperdisk Balanced attached to the reader VM | Keep the full corpus being served as ordinary text segments on mounted SSD storage, accessible to reader processes through the open read contract |
| Durable backing and recovery | Google Cloud Storage, Standard storage class | Preserve received text in immutable object generations; used for ingestion durability and restoration, not normal query-time range fetches |
| Committed append history | Cloud SQL for PostgreSQL | Operational journal: entry identity, committed position, object/segment locators and generations, length, integrity data, and publication state |
| HTTP service and nearby reader execution | One Google Compute Engine Linux VM running Docker | Small append/read/follow service; independent reader programs as ordinary processes/containers |
| Reader working storage | Hyperdisk Balanced on the same VM | Reader-owned indexes and caches in separate working space; independently rebuildable |
| First example search reader | Tantivy | Incremental lexical/phrase search with references back to original text; a replaceable reader, not part of capture |

Keep the bucket, database, and compute in the same region, using a VM type that supports Hyperdisk Balanced. Choose machine sizes, provisioned IOPS/throughput, and database availability settings from measured demand and the accepted operating budget. This recommendation incurs fixed VM and managed-database costs plus a full SSD serving copy; no price or latency claim has been established.

## Read-path correction

The previous version put only reader indexes and caches on disk. That leaves a new reader or raw-text transform dependent on object-storage reads. Same-region placement alone does not resolve that weakness.

Normal scans and range reads should operate on the mounted text corpus and the OS page cache. GCS is the durable backing copy; it should not be fetched range by range on the ordinary read path. This is a complete serving copy, not an index-only or best-effort hot cache.

Hyperdisk is network-attached block storage, not physically local NVMe. Google describes Hyperdisk Balanced as a low-latency SSD option; actual performance depends on provisioning, VM limits, and access patterns. Physically attached Local SSD is temporary storage and is not the durable authority in this recommendation. [Hyperdisk](https://docs.cloud.google.com/compute/docs/disks/hyperdisks), [Local SSD](https://docs.cloud.google.com/compute/docs/disks/local-ssd).

The corpus being served must fit the provisioned serving storage. If an append cannot fit, do not publish or acknowledge it until capacity is available; already committed reads can continue. Capacity growth and restore readiness must be explicit; do not silently turn the design into on-demand object fetching when disk space runs out. This does not establish an infinite-capacity single-machine design. Compare cold block reads, warm reads, and sustained scans before committing to machine or disk sizes.

## Why this combination

GCS provides object storage and resumable uploads for the backing copy. Physical segmentation preserves long logical entries without imposing a semantic model. Object completion is not the same thing as a committed Pit append. Retaining GCS on the append path preserves the existing durability recommendation while moving it off the normal read path. [GCS uploads](https://docs.cloud.google.com/storage/docs/resumable-uploads).

PostgreSQL supplies transactions for the small ordered journal. Cloud SQL keeps that journal independent of the reader VM and provides managed backup/recovery options. The journal describes where preserved text is and whether it is committed; it does not interpret content. Backup, point-in-time recovery, and availability configuration must be explicit before deployment. [Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/introduction), [recovery](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr).

A Compute Engine VM provides ordinary execution against the mounted original text and reader working storage. Reader code can stream originals, build an index, or run its own transform without being expressed as a particular database's UDF. Start with existing container/process management. [Hyperdisk](https://docs.cloud.google.com/compute/docs/disks/hyperdisks).

Tantivy is an embedded full-text search library with incremental indexing and phrase search. We build a thin example reader around it. Other readers can bypass it completely and build different artifacts from the same text. [Tantivy](https://github.com/quickwit-oss/tantivy).

## What we implement

The custom core is a small HTTP service for append, original reads/ranges, and replay/follow, plus publication/recovery logic. The read contract remains independent of any example search API. Reader programs have access to originals and their own writable derived state.

Complete and verify both the on-disk serving copy and the GCS backing upload before publishing its journal entry. Serialize committed-position allocation within the journal transaction so concurrent commits cannot produce a traversal cursor that skips a late commit. Acknowledge after the journal commit. Retries must resolve to a known result, and abandoned uploads must be distinguishable from committed history. This is a recoverable publication workflow, not a claim of a shared disk/GCS/PostgreSQL transaction. Object-storage work remains part of append latency; it is removed from ordinary retrieval latency.

Test reader-VM replacement, reattachment or rebuilding of the serving disk, and interruption at publication boundaries. After serving-copy loss, report restoration/readiness explicitly rather than promising normal query latency during recovery. Test database recovery against its declared failure model; managed storage does not imply zero loss for every disaster scenario. Regional HA, if selected, is a separate operating choice from backup restoration. [Cloud SQL HA](https://docs.cloud.google.com/sql/docs/postgres/high-availability).

BigQuery and Splunk remain optional reader implementations. They are not dependencies of this initial core. The same source-independent text can support them later.

## Verification gate

Carry forward the [solution-space checks](problem-weave.md#risk-retirement-plan): exact preservation, streamed long entries, committed-history recovery, a later reader working while the first index is unavailable, and complete preparation/query/freshness/data-movement accounting. Specifically demonstrate raw reading by that later reader with object-storage access unavailable, while the serving copy is healthy. Measure serving-copy capacity and restoration time separately from steady-state query latency. Compare with simpler alternatives where they challenge a critical assumption. This stack was an unvalidated recommendation and has since been withdrawn; these checks are retained as proposal history.
