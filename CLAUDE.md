# CLAUDE.md

Guidance for Claude Code (or any contributor) working in this repo. Read `docs/design.md` for the full system design — this file is the build plan and decision log distilled from it, kept in sync as work progresses.

## What this project is

BG Center: a web chat where ~10 friends ask questions about each other and get answers grounded in a Markdown doc each member wrote. v1 is a RAG chatbot on a hosted open LLM; v2+ turns it into an agent with tools. Full detail: `docs/design.md`.

## How to use this file

- Work the checklist below **in order** — later steps assume earlier ones exist (e.g. there's no retrieval to build before there's a chunked, embedded corpus).
- One branch + one PR per step, small conventional commits (`feat:`, `fix:`, `eval:`, `docs:`) — see `docs/design.md` § "How work lands".
- When a step involves a real architectural choice not already covered by an existing ADR, write a new one in `docs/decisions/000N-*.md` (context, options, decision, consequences) **before** implementing it, and add it to the decision log below. Don't silently make an architectural choice only in code.
- Tick a box here in the same PR that completes it, so this file always reflects real repo state, not aspiration.
- Each phase (v1, v2, v3, v4) ends with a git tag matching the roadmap gates in `docs/design.md` § Roadmap.

## Decision log

Full rationale lives in `docs/decisions/`; this is the index. When you make a new consequential decision, add a row here and the ADR it links to.

| ADR | Decision | Why (one line) |
|---|---|---|
| [0001](docs/decisions/0001-llm-and-embeddings.md) | Ollama locally, hosted Groq (OpenAI-compatible) in prod; Qwen family shortlisted; multilingual-e5/bge-m3 embeddings on CPU | No GPU budget for 24/7 hosting; config-driven model choice survives provider churn |
| [0002](docs/decisions/0002-deployment-platforms.md) | Managed platforms for every component (Vercel/Netlify, Render/Fly.io, Neon/Supabase, Langfuse Cloud) | Time goes into the AI/retrieval work, not ops, for a 10-user hobby project |
| [0003](docs/decisions/0003-two-repo-split.md) | Public `bg-center` (code) + private `bg-center-data` (real docs), split by content not by copy | Public repo's commit history is the real history; real personal data never enters it, so it can't leak through it |
| [0004](docs/decisions/0004-data-model.md) | One Markdown file per member, YAML frontmatter for facts + `##` sections for free text | Serves RAG now, needs zero restructuring when the v2 `query_facts` tool arrives |
| [0005](docs/decisions/0005-eval-strategy.md) | Two eval tracks (public fictional "sample" in CI, private "real" before releases) sharing one runner, cheapest-metric-first | Fast public CI signal without ever putting real friends' Q&A in public logs |

**Open questions still unresolved** (see `docs/design.md` § Open questions — resolve before the step they block):
- PT/EN mix of real docs — decides the embedding model and eval split. Blocks: picking the final embeddings model in step 3.
- Member count and total doc length — if under ~20k tokens, the stuff-everything baseline may simply win. Blocks: taking the "RAG beats baseline" done-criterion seriously in step 9.
- Who approves edits to someone else's doc once runtime editing exists — not a v1 blocker, revisit at v3.

## v1 — RAG MVP build plan

Gate to v2: all boxes below checked, plus `docs/design.md` § "Definition of done" (90%+ fact accuracy, 90%+ correct declines, every answer traceable, eval report states RAG-vs-baseline).

### 1. Repo and data scaffolding
- [x] Public `bg-center` repo created, monorepo structure in place (`backend/`, `frontend/`, `data/sample/`, `evals/`, `docs/`, `.github/workflows/`)
- [x] Private `bg-center-data` repo created (empty, awaiting real member docs)
- [ ] Fictional sample members written in `data/sample/` (ADR-0004 format): enough members to mirror the planned real group's size, with planted traps per `docs/design.md` § Evals (lookalike names, shared facts, clear extremes, cross-member stories, deliberately missing facts)
- [ ] First real member doc written and approved by that friend, pushed to `bg-center-data` (consent process starts here, not at the end — see `docs/design.md` § Privacy and safety)

### 2. Backend skeleton
- [ ] FastAPI app in `backend/` boots locally (`uvicorn`), health check endpoint
- [ ] Config loaded from environment (`.env`, see `.env.example`) — model name, base URL, `DATA_DIR`, secrets; nothing hardcoded (ADR-0001)
- [ ] Dependency manifest (`pyproject.toml` or `requirements.txt`) and lint/type-check config (ruff, mypy) added

### 3. Ingestion
- [ ] Parser: Markdown + YAML frontmatter → structured facts + list of `##` sections (ADR-0004)
- [ ] Chunker: one chunk per section, split only past ~400 tokens; member-name prefix before embedding; `member`/`section`/`source_file` metadata per chunk
- [ ] One synthesized "facts" chunk per member, rendered from frontmatter
- [ ] Embeddings model picked from the ADR-0001 shortlist, loaded on CPU; in-memory Chroma index built at startup from `DATA_DIR`

### 4. Chat pipeline
- [ ] Query rewrite: last 4 turns → standalone question
- [ ] Retrieval: top-k over the Chroma index
- [ ] Prompt assembly: retrieved chunks + system prompt instructing the model to decline when the answer isn't in context (this is the primary anti-hallucination control, backed by the unanswerable/adversarial eval categories)
- [ ] Streamed generation against the configured LLM provider (ADR-0001)
- [ ] Stuff-everything baseline implemented behind a config flag, so every eval run can compare against it (ADR-0005)

### 5. API
- [ ] `POST /api/auth` — invite code → bearer token
- [ ] `GET /api/members` — member list for the UI strip
- [ ] `POST /api/chat` — SSE stream of `token` events, then `done` with `sources`
- [ ] `POST /api/feedback` — thumbs rating (+ optional comment), `204`
- [ ] CORS locked to the frontend origin from day one

### 6. Frontend
- [ ] React + TypeScript app in `frontend/`: invite gate, member strip, chat view, sources display, thumbs up/down
- [ ] SSE consumption via plain `fetch` (no websockets), matching the backend contract

### 7. Observability
- [ ] Langfuse Cloud (EU region) wired in; one trace per chat request, with request/query-rewrite/retrieval/generation/feedback spans per `docs/design.md` § Trace contents
- [ ] Structured JSON app logs with a request ID shared with the Langfuse trace

### 8. Storage
- [ ] Postgres (Neon or Supabase free tier) for conversations and feedback

### 9. Evals
- [ ] `evals/sample_golden.yaml` — 30–40 questions across all seven categories (single-member fact, story, cross-member, follow-up, unanswerable, adversarial, Portuguese), using `data/sample/`
- [ ] Eval runner: recall@k (deterministic) → string checks → LLM-as-judge (different model than the answerer, ADR-0001), reports scores by category
- [ ] Baseline vs RAG at k = 3, 5, 8, across the shortlisted candidate models — run and recorded, to make the final model/k pick an eval-driven decision, not a guess
- [ ] Real golden set authored privately in `bg-center-data`, run locally before the v1.0 tag

### 10. CI/CD
- [ ] `.github/workflows/ci.yml` filled in for real: lint, type-check, unit tests, secret scan on every push; eval suite on sample data + PR comment on pull requests
- [ ] Auto-deploy wired through each host's GitHub integration on merge to `main`

### 11. Privacy and access
- [ ] Invite-code → short-lived token flow enforced on every endpoint except `/api/auth`
- [ ] Rate limiting per token
- [ ] Group told explicitly that chats are logged and admin-readable; Langfuse trace retention set to 30 days
- [ ] Doc/chunk removal path exists for any member who asks

### 12. Ship v1
- [ ] All "Definition of done" criteria in `docs/design.md` met
- [ ] README's eval results table filled in with real baseline-vs-RAG numbers
- [ ] Tag `v1.0`

## Roadmap after v1 (summary — detail in `docs/design.md` § Roadmap to agent)

| Phase | Starts when | Adds |
|---|---|---|
| v2 · First tools | Gate 1: v1 done-criteria met | `search_stories(query, member?)`, `query_facts(filter)`, hand-written agent loop (no framework yet) |
| v3 · Memory + games | Gate 2: cross-member eval ≥ 80% | Write tools (new lore, pending approval), quiz mode, storage moves to Postgres + pgvector |
| v4 · Multi-step | Gate 3: writes need approval, working well | Event planner, web search + polls, roast/toast writer; multi-agent only if one agent gets unwieldy |

Do not start a phase's work before its gate passes on the eval set — the gates exist specifically so scope doesn't creep ahead of evidence that the simpler version works.
