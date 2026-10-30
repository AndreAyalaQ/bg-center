# ADR-0004: Markdown + YAML frontmatter as the member data model

## Status
Accepted — 2026-10-29

## Context
Each member needs to be represented in a way that supports two different access patterns: narrative/semantic retrieval ("what happened to João in Porto?") and structured aggregate queries ("who's the oldest?"). The MVP only needs to serve the first pattern well (RAG); the second pattern is expected to score poorly until the v2 `query_facts` tool exists, but the data model must not need restructuring when that tool is added.

## Options considered
- **Database-first** (e.g. a Postgres table of facts plus a separate text blob table): aggregate queries are easy from day one, but requires runtime infrastructure and a facts/story split that doesn't exist yet, and over-builds for a 10-person MVP.
- **Markdown + YAML frontmatter per member** (one file per person): frontmatter holds structured facts (birthday, city, job, pets, diet, height), the body holds free-text `##` sections (Personality, Stories, Inside jokes). Git-native, human-editable by the friend who owns the doc, and trivially split into "facts chunk" + "story chunks" for RAG now.

## Decision
One Markdown file per member, YAML frontmatter for structured facts, `##` sections for free text. The frontmatter is also rendered into one short synthesized "facts" chunk per member for the MVP's RAG index, so aggregate questions aren't completely unanswerable before v2 — they're just expected to be weak, which is the intended motivation for building the `query_facts` tool next.

**Chunking rule:** one chunk per `##` section, split further only if a section exceeds ~400 tokens. Each chunk is prefixed with the member's name before embedding (e.g. "Miguel (Migas) – Stories: ...") so the vector carries who it's about. Every chunk carries `member`, `section`, `source_file` metadata.

**Storage path (MVP → later):**

| Data | MVP | Later |
|---|---|---|
| Member docs | Markdown files in the repo | Postgres, editable at runtime |
| Vectors | In-memory Chroma, built at startup | pgvector |
| Structured facts | Frontmatter, parsed at startup | Postgres table behind a query tool |
| Conversations, feedback | Postgres | Postgres |

## Consequences
- No migration is needed when v2 adds `query_facts(filter)` — it reads the same frontmatter that's already being parsed at startup for the facts chunk.
- No migration is needed when v3 moves storage to Postgres + pgvector — the Markdown files are the source of truth and get imported, not redesigned.
- Aggregate questions scoring poorly in the v1 golden set evals is expected and intentional (see `docs/design.md` § Roadmap, Gate 2), not a bug to fix within v1.
