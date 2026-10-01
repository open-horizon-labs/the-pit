# V1 table contract

Status: agreed hash-uniqueness design for Supabase PostgreSQL. The user explicitly confirmed that repeats do not matter and avoiding duplicate accumulation does. The live `entries` table in project `iunbpyiylsbkscjaisid` was inspected on 2026-09-30 and matches this contract. Authenticated content-only insert, exact readback, and duplicate receipt preservation were verified.

Sinks insert text directly into one table. The only required input is `content`.

Use the SHA-256 hash of the exact content as the entry ID. Identical text has one stored entry, regardless of which sink supplied it. Repeated receipt occurrences are not recorded.

The live generated expression uses `extensions.digest`; a Unicode-containing transcript's database ID matched the SHA-256 of its UTF-8 bytes.

```sql
create table public.entries (
    id text generated always as (
        encode(extensions.digest(content, 'sha256'), 'hex')
    ) stored primary key,
    received_at timestamptz not null default clock_timestamp(),
    content text not null
);
```

| Column | Meaning |
|---|---|
| `id` | Database-computed SHA-256 of `content`, encoded as 64 lowercase hexadecimal characters. It is both the stable reference and the uniqueness key; sinks do not supply it. |
| `received_at` | Database wall-clock time evaluated during insertion when omitted by the sink. Receipt bookkeeping, not the date described in the text or a commit timestamp. |
| `content` | The original text supplied by the sink. Whitespace and formatting are preserved. Empty text is allowed; null is not. Identical text is stored once. |

Example using a parameterized database connection:

```sql
insert into public.entries (content)
values ($1)
on conflict (id) do nothing
returning id, received_at;
```

There is no application-specific size constraint, content interpretation, or normalization. Deduplication uses the bytes of stored text: case, whitespace, line endings, and Unicode normalization differences remain distinct. The earlier 50 MB figure is a planning reference, not an enforced limit. PostgreSQL and the chosen connection/API path still have their own practical limits.

The primary key is the only index required by this table definition. Search indexes and derived state belong to readers and can be added independently.

## Write and read semantics

- Use insert-only sink access and select access for readers. The applied [grants](access.sql) and [account policies](client-policy.sql) enforce this for the current plugin account on `entries`; the DDL alone does not. Ordinary sink credentials must not permit updates, deletes, or truncation. Administrators retain administrative capabilities. Other tables in the existing project were not changed.
- Sinks normally omit `received_at`. Column privileges can reserve that field for the database default when access is configured.
- Duplicate content leaves the existing row and its original `received_at` unchanged. This records a growing corpus of unique text, not every occurrence of a receipt. No occurrence count or last-seen timestamp is maintained.
- `RETURNING` returns the new row only when an insert happens. With `DO NOTHING`, a conflict returns no row; do not treat that as a failed write. A sink that needs the existing row can calculate the same hash and read by ID in a subsequent statement with suitable read permissions. Do not use `DO UPDATE` merely to obtain a returned row.
- Hash-based uniqueness accepts the practical SHA-256 collision assumption; it is not a mathematical guarantee that different text can never share an ID.
- `received_at` supports chronological inspection. Neither it nor the content hash is a commit-ordered cursor. A reader that polls only after its latest timestamp can miss a concurrent transaction that commits late. Reliable follow/replay remains a separate read-interface decision; do not add custom write coordination to this schema merely to imply it is solved.

References: [PostgreSQL pgcrypto hashing](https://www.postgresql.org/docs/current/pgcrypto.html#PGCRYPTO-HASH-FUNCS), [generated columns](https://www.postgresql.org/docs/current/ddl-generated-columns.html), [INSERT and ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html), [clock functions](https://www.postgresql.org/docs/current/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT).

## Independent reader index

On 2026-10-01, readers.sql deployed pg_trgm and the reader-owned GIN index entries_content_trgm_idx over content, plus SECURITY INVOKER search/range functions. These are replaceable read facilities; the authoritative table remains id, received_at, content.
