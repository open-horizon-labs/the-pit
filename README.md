# The Pit

The Pit stores unstructured text so agents can recover earlier context and build their own search tools. It preserves the exact text received, stores identical text once, and provides direct reads, search, and bounded excerpts with citations to the original.

## Store text without imposing a model

Text can come from a conversation, an email, a repository, or any other source. Capture does not require classification, entities, source metadata, or a document schema. Source-specific interpretation belongs to independent readers.

Each entry contains its text, a database-computed SHA-256 identity, and its first receipt timestamp. Repeated submissions of identical text leave the original entry unchanged. Receipt time records when Pit received the text, not when the events described in it happened.

Pit does not impose an application-specific entry-size limit or silently truncate captured text. Database and transport limits still apply. External mirrors may change text before submitting it; Pit preserves what it receives.

See the [table contract](schema.md) for storage and deduplication details.

## Capture and retrieve

The [plugin](plugin.md) provides tools for saving and retrieving context, local conversation capture, and metadata-only usage metrics. External mirrors such as Make or Zapier can also submit text.

Readers can use:

- **Literal search:** find a phrase and return original text around the first match in each entry. [Search and range reads](retrieval.md).
- **Ranked queries:** supply keywords and retrieve ranked passages with exact character ranges and explicit coverage limits. [Query API and installation](query.md).
- **Range reads:** expand a useful passage by its entry hash and character offsets.
- **Direct reads:** build independent indexes, searches, and transformations over the preserved corpus.

Search and ranking run in PostgreSQL before results are transferred. Indexes and transformations belong to readers and can be replaced without changing capture or the stored text.

Retrieved text is historical evidence. It may be incomplete or outdated; search results do not establish the current state of the systems they describe.

## Installation

Pit uses Supabase PostgreSQL. Personal storage and the hosted, tenant-private service have separate setup instructions:

- [Plugin setup and usage](plugin.md)
- [Hosted service setup and verification](saas/README.md)
- [Portable hosted plugin](saas/plugin/INSTALL.md)
- [Ranked query SQL and MCP setup](query.md#installation-and-rollback)
- [Usage metrics](metrics.md)

## Design and development

A reliable commit-ordered follow/replay interface remains open. Receipt-ordered reads are not a substitute for a commit cursor.

See the [design framing](problem-weave.md), [implementation notes](implementation-recommendation.md), [hosting comparison](managed-options.md), and [retrieval verification](retrieval-adoption.md) for decisions, experiments, and unresolved questions. Contributor constraints are in [AGENTS.md](AGENTS.md).
