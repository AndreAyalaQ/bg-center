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
- [x] Fictional sample members written in `data/sample/members/` (ADR-0004 format): 6 members (joao, joana, rita, tomas, ines, diogo) with planted traps per `docs/design.md` § Evals (lookalike names/nicknames, shared facts, clear extremes, cross-member stories, a stale fact, a missing field, PT/EN mix, an indirect prompt injection)
- [ ] First real member doc written and approved by that friend, pushed to `bg-center-data` (consent process starts here, not at the end — see `docs/design.md` § Privacy and safety)

### 2. Backend skeleton
- [x] FastAPI app in `backend/` boots locally (`uvicorn`), `/health` endpoint — verified: boots, responds `{"status":"ok",...}`, CORS echoes only the configured `FRONTEND_ORIGIN`
- [x] Config loaded from environment (`.env`, see `.env.example`) — model name, base URL, `DATA_DIR`, secrets; nothing hardcoded (ADR-0001). `app/config.py`, pydantic-settings
- [x] Dependency manifest (`backend/pyproject.toml`) and lint/type-check config (ruff, mypy) added — `pytest`, `ruff check`, `mypy` all pass clean

### 3. Ingestion
- [x] Parser (`app/ingest/parser.py`): Markdown + YAML frontmatter → structured facts + list of `##` sections (ADR-0004). PT and EN headings (e.g. "Histórias"/"Stories") collapse to the same language-independent slug via `slugify_section`
- [x] Chunker (`app/ingest/chunker.py`): one chunk per section, split past ~400 tokens (≈1600 chars, paragraph-boundary split); every chunk prefixed with first name + nickname before embedding; `member`/`section`/`source_file` on every chunk
- [x] One synthesized "facts" chunk per member, rendered from frontmatter (`render_facts`) — fields absent from frontmatter are omitted, not guessed at, so the `unanswerable` eval trap (e.g. Diogo's missing `pets`) stays genuinely unanswerable
- [x] Embeddings model picked from the ADR-0001 shortlist (`intfloat/multilingual-e5-small`, set via `EMBEDDINGS_MODEL`), loaded on CPU (`app/ingest/embeddings.py`); in-memory Chroma index built at startup from `DATA_DIR` (`app/ingest/index.py`, wired into FastAPI's lifespan in `app/main.py`) — verified live: 31 chunks indexed from the 6 sample members, sane top-k recall on single-fact and cross-lingual queries, and the "who has cats" aggregate query reproduces the expected false-positive (Tomás is allergic, not an owner) that motivates the v2 `query_facts` tool

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
- [x] Sample golden set: 61 cases (24 hand-written in `evals/sample_golden.yaml` + 37 generated by `evals/generate_fact_questions.py` from member frontmatter into `evals/sample_golden.generated.yaml`), across 9 categories — the original 7 split into single_fact/cross_member/lookalike/stale_fact/story/follow_up/unanswerable/adversarial/injection for sharper failure localization
- [ ] Eval runner (`evals/run.py`): recall@k (deterministic) → string checks → decline check → LLM-as-judge rubric (different model than the answerer, ADR-0001), reports scores by category, always compared against the stuff-everything baseline
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

## Retrieval quality backlog (not gated to v1)

Pure dense-vector retrieval (current state) is a reasonable first pass, not the ceiling of what's possible — see the "Is this the gold standard?" discussion in `docs/decisions/0001-llm-and-embeddings.md`'s revert note. Two concrete upgrades to pick up once the eval runner (step 9) exists to actually measure them, rather than adopting on faith:

- **Hybrid retrieval (BM25 + dense).** Add a sparse/keyword index (e.g. `rank_bm25` or similar) alongside the existing Chroma dense index, and combine both result sets (e.g. reciprocal rank fusion) before taking top-k. Dense embeddings blur on exact names/nicknames — we already saw this directly: the Tomás PT city-query recall miss (ADR-0001's revert note) happened because his name is semantically diluted by appearing in other members' "Porto trip" story chunks, which is exactly the kind of exact-match case BM25 is strong at and dense retrieval is weak at. The `lookalike` eval category (João/Joana, Pi/Pipo) is likely to benefit the same way.
- **Reranking.** Retrieve a wider candidate set cheaply (e.g. top-20 via hybrid search), then rerank down to the final top-k with a cross-encoder (e.g. a small multilingual reranker like `bge-reranker-v2-m3` or similar). Cross-encoders score query+passage jointly rather than via separate embeddings, which is typically the single biggest retrieval-quality lever in production RAG systems — at the cost of being too slow to run over the full corpus, hence "retrieve wide, rerank narrow."

**Gate:** implement behind a config flag (same pattern as the stuff-everything baseline), and only keep enabled by default if the golden-set eval run shows a measurable improvement over plain dense retrieval — consistent with ADR-0005's "always compared against the baseline" philosophy, extended to compare hybrid+reranked vs dense-only. Whichever one lands first gets its own ADR with real before/after eval numbers, per this project's normal convention — this backlog entry isn't that ADR.

## Roadmap after v1 (summary — detail in `docs/design.md` § Roadmap to agent)

| Phase | Starts when | Adds |
|---|---|---|
| v2 · First tools | Gate 1: v1 done-criteria met | `search_stories(query, member?)`, `query_facts(filter)`, hand-written agent loop (no framework yet) |
| v3 · Memory + games | Gate 2: cross-member eval ≥ 80% | Write tools (new lore, pending approval), quiz mode, storage moves to Postgres + pgvector |
| v4 · Multi-step | Gate 3: writes need approval, working well | Event planner, web search + polls, roast/toast writer; multi-agent only if one agent gets unwieldy |

Do not start a phase's work before its gate passes on the eval set — the gates exist specifically so scope doesn't creep ahead of evidence that the simpler version works.
