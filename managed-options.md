# Managed hosting: developer experience and entry cost

Checked 2026-09-30. After this comparison, the user identified Supabase as personally the least hassle. Supabase PostgreSQL is now the preferred v1 platform; no paid plan or deployment has been authorized by that preference alone. The user subsequently removed enforcement of the 50 MB cap when deciding the [table contract](schema.md); 5 MB was discussed hypothetically.

For ease of implementing and maintaining the append/read core, the assistant favors managed PostgreSQL. Ordinary PostgreSQL transactions and tooling reduce custom application work. ClickHouse Cloud also manages the infrastructure, but its analytical insert/query model requires more specialized design. This is an engineering assessment, not measured implementation effort.

## Small continuously running database

USD, before tax. These are entry configurations with different resources, not equal-throughput benchmarks or a complete Pit operating budget.

| Service | Monthly starting calculation | Included resources / qualifications |
|---|---|---|
| Supabase Pro | $25 for a new Pro organization with one Micro project | 1 GB RAM, shared compute, 8 GB database disk, daily backups retained 7 days. Higher compute, disk, and usage cost more. |
| Neon Launch | $19.35 compute at 0.25 CU × $0.106 × 730 hours, plus $0.35/GB-month storage | Approximately 1 GB RAM at this size. History/restore storage, snapshots, and excess transfer are additional. Disable scale-to-zero for continuously active compute. |
| ClickHouse Cloud Basic | Approximately $160 compute for a month active 24 hours/day, plus storage, backups, and transfer | Official AWS us-east-1 example uses one replica, 8 GiB RAM and 2 vCPU. More hardware than the PostgreSQL entry configurations; single availability zone. Region changes pricing. |

Sources: [Supabase pricing](https://supabase.com/pricing), [compute sizes](https://supabase.com/docs/guides/platform/compute-and-disk), [Neon pricing](https://neon.com/pricing), [Neon compute configuration](https://neon.com/docs/manage/endpoints/), [ClickHouse billing examples](https://clickhouse.com/docs/cloud/manage/billing/overview).

Neon can cost less for light intermittent usage when compute is allowed to suspend. That introduces wake-up behavior; it is not the same operating assumption as the continuously active comparison. Within an existing paid Supabase organization, an additional Micro project starts around $10/month if its shared compute credit is already consumed. No existing subscription or spare credit has been verified for this task. [Supabase billing](https://supabase.com/docs/guides/platform/billing-faq).

## Execution freedom remains a separate requirement

Managed PostgreSQL supports SQL functions and provider-supported extensions; it does not provide unrestricted execution on the database host. Supabase does not grant superuser access and disallows `COPY FROM PROGRAM`. General reader programs should be budgeted and placed separately, near the database, when they cannot use supported in-database facilities. Their compute and data movement are not included in the database-only figures. [Supabase restrictions](https://supabase.com/docs/guides/database/postgres/roles-superuser), [extensions](https://supabase.com/docs/guides/database/extensions).

Supabase offers PGroonga as an additional text-search option. This establishes an available extension, not a verified 50 MB indexing solution or a reader requirement. [PGroonga](https://supabase.com/docs/guides/database/extensions/pgroonga).

ClickHouse Cloud executable Python UDFs are public beta, with network-access UDFs separately in private beta. Cloud uses object storage internally; the earlier SSD-backed installation and the managed service have different cold-read behavior that has not been measured here. [Cloud UDFs](https://clickhouse.com/blog/executable-udfs-clickhouse-cloud-beta), [Cloud storage](https://clickhouse.com/docs/cloud/manage/billing/overview).

## Recommendation under this lens

Supabase Pro is the practical predictable-cost starting candidate for an always-running managed PostgreSQL core. Neon is a strong lean alternative, particularly for intermittent development. ClickHouse remains the search/scan/transform-oriented comparator. Prioritizing developer experience and initial expense shifts the preference toward PostgreSQL; it does not establish that a $25 database meets the complete open-reader/nearby-compute requirement.
