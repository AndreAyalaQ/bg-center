# BG Center

A web chat where a friend group asks questions about its own members and gets answers grounded in docs each member wrote. Starts as a RAG chatbot on open-source models (v1), grows into an agent with tools (v2+).

Full system design: [`docs/design.md`](docs/design.md). Architecture decisions and their rationale: [`docs/decisions/`](docs/decisions/). Build plan for contributors (including Claude Code sessions): [`CLAUDE.md`](CLAUDE.md).

## Status

🚧 v1 in progress. Runnable end-to-end against the fictional sample group: backend (ingestion, RAG chat pipeline, API), frontend, and an eval dashboard all work today, live-verified against a local Ollama model. Not yet done: Postgres-backed storage (chat history and feedback are in-memory and don't survive a restart), Langfuse observability, CI/CD, and the real member docs (private repo, pending consent). See `CLAUDE.md` for the full step-by-step checklist and what's still open.

**Try it locally:** [Local development](#local-development) below gets you a running chat against the 6 fictional sample members in about five minutes (plus one local LLM install).

## Architecture

```
React frontend (Chat UI, SSE stream)  --HTTPS-->  FastAPI backend
                                                      1. Query rewrite (last 4 turns -> standalone question)
                                                      2. Retrieve top-k (LangChain + Chroma, in-memory)
                                                      3. Grounded answer (streamed, SSE)
                                                      <--> Member docs (data/sample/, or private bg-center-data)
                                                      <--> LLM (Ollama locally, Groq/OpenRouter/Together in prod)
                                                      --> conversation/feedback store (in-memory today, Postgres planned)
                                                      --> Langfuse (traces + evals) — not wired up yet
```

See `docs/design.md` § Architecture for the full request flow.

## Repository layout

```
bg-center/
├── backend/           FastAPI app (auth, members, chat SSE, feedback), RAG pipeline, tests — see backend/README.md
├── frontend/           React + TypeScript chat UI (invite gate, member strip, sources, thumbs) — see frontend/README.md
├── data/sample/         fictional members — used by tests, CI, demos (6 members, planted eval traps)
├── evals/               golden set (61 cases) + eval runner + Gradio dashboard — see evals/README.md
├── docs/
│   ├── design.md        full system design
│   └── decisions/        one ADR per major decision
└── .github/workflows/    CI (not filled in yet)
```

Real member docs live in a separate **private** repo, `bg-center-data` — never in this repo. See `docs/decisions/0003-two-repo-split.md` for why.

## Local development

Everything below runs against the 6 fictional sample members in `data/sample/`.

```bash
cp .env.example .env   # INVITE_CODE, LLM provider settings, etc.
```

**1. Backend** (FastAPI + RAG pipeline — full detail in `backend/README.md`):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch>=2.2"
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
# -> http://127.0.0.1:8000/health should report indexed_chunks: 31
```

By default this talks to a local Ollama server (`LLM_BASE_URL` in `.env.example`) — install Ollama and pull a model (e.g. `ollama pull qwen3.5:9b`) first, or point `LLM_BASE_URL`/`LLM_MODEL` at a hosted provider (Groq, OpenRouter, Together — all OpenAI-compatible, ADR-0001).

**2. Frontend** (React chat UI — full detail in `frontend/README.md`):

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
# -> http://localhost:5173, log in with INVITE_CODE from the root .env
```

**3. Eval dashboard** (optional, Gradio — full detail in `evals/README.md`):

```bash
cd backend && .venv/bin/pip install -e ".[ui]"
cd .. && backend/.venv/bin/python -m evals.eval_ui
# -> http://127.0.0.1:7860 — retrieval metrics (MRR/nDCG/coverage) and LLM-judge generation scoring
```

## Evals

Every change to prompt, chunking, top-k, or model is judged against a golden question set (61 cases across 9 categories, `evals/sample_golden.yaml` + generated fact questions), compared against a stuff-everything baseline. See `docs/decisions/0005-eval-strategy.md` and `evals/README.md`.

Retrieval metrics (MRR, nDCG, keyword coverage) and LLM-as-judge generation scoring (Accuracy/Completeness/Relevance) both run today via `evals/eval_ui.py`. The systematic baseline-vs-RAG comparison across k=3/5/8 and candidate models, and the real-data run against actual friends' docs, are still open — see `CLAUDE.md` step 9.

| Version | Baseline | RAG | Agent |
|---|---|---|---|
| v1 | — | — | — |

*(Table fills in once the full baseline-vs-RAG comparison run — CLAUDE.md step 9 — is done.)*
