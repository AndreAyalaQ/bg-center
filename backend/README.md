# backend

FastAPI app and RAG pipeline. Ingestion, the chat pipeline, and the API endpoints are built; the frontend (step 6) is not yet — see `docs/design.md` and the root `CLAUDE.md` build plan.

## Layout

```
backend/
├── app/
│   ├── main.py            FastAPI app, CORS, /health; builds the member index at startup
│   ├── config.py           Settings loaded from the environment (ADR-0001)
│   ├── ingest/
│   │   ├── parser.py        Markdown + YAML frontmatter → Member/Section (ADR-0004)
│   │   ├── chunker.py        Member -> embeddable Chunks, incl. the synthesized facts chunk
│   │   ├── embeddings.py      LangChain HuggingFaceEmbeddings wrapper, e5 prefix convention (ADR-0001, ADR-0006)
│   │   └── index.py           LangChain Chroma vectorstore, in-memory, built at startup (ADR-0006)
│   ├── chat/
│   │   ├── llm.py             OpenAI-compatible client — Ollama locally, Groq/OpenRouter/Together in prod (ADR-0001)
│   │   ├── rewrite.py          Last-4-turns -> standalone question
│   │   ├── prompt.py            Grounded-answer system prompt (decline + injection defense)
│   │   └── pipeline.py           Orchestrates rewrite -> retrieve -> prompt -> stream
│   └── api/
│       ├── schemas.py          Request/response pydantic BaseModels, camelCase on the wire
│       ├── auth.py              Invite-code -> JWT; require_token dependency
│       ├── store.py              In-memory conversation/feedback store (placeholder until Postgres, step 8)
│       └── routes.py              /api/auth, /api/members, /api/chat (SSE), /api/feedback
├── chat_ui.py              Gradio chat tester — calls run_chat() directly, no server/auth needed
├── tests/
└── pyproject.toml
```

The eval dashboard (`evals/eval_ui.py`, retrieval metrics + LLM-judge generation scoring) lives alongside the golden set in `evals/` — see `evals/README.md`.

Data classes (`Member`, `Section`, `Chunk`, `RetrievedChunk`, `ChatTurn`) are pydantic `BaseModel`s, not `@dataclass` (ADR-0006) — the one exception is `ChatResult` in `pipeline.py`, which carries a live streaming `Iterator[str]` that doesn't fit pydantic's validate/serialize model.

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch>=2.2"  # CPU-only, avoids pulling in CUDA
.venv/bin/pip install -e ".[dev]"
cp ../.env.example ../.env   # fill in values; loaded from the repo root
```

The embeddings stack (`langchain-huggingface` → `sentence-transformers` → `torch`, plus `langchain-chroma` → `chromadb`) is a real install — expect roughly 1–2GB of downloads and disk. The embedding model itself (~470MB) downloads from the Hugging Face Hub on first use and is cached afterward.

For local chat pipeline development, point `LLM_BASE_URL` at a running Ollama instance (see `.env.example`); if using a thinking-enabled model (e.g. `qwen3.5`), also set `LLM_NUM_CTX=16384` or similar — see `docs/decisions/0001-llm-and-embeddings.md`'s "Update — 2026-11-01" for why.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
# -> GET http://127.0.0.1:8000/health
# {"status":"ok","environment":"development","indexed_chunks":31}
```

`indexed_chunks` confirms the startup ingestion actually ran: parse `DATA_DIR` → chunk → embed → build the in-memory index.

Interactive API docs (OpenAPI, generated from the pydantic schemas) at `http://127.0.0.1:8000/docs`. Every endpoint except `POST /api/auth` requires `Authorization: Bearer <token>`, obtained by posting `INVITE_CODE` to `/api/auth`.

Conversation and feedback storage is in-memory (`app/api/store.py`) until Postgres lands (step 8) — history and feedback don't survive a restart yet.

### Dev tools (Gradio)

```bash
.venv/bin/pip install -e ".[ui]"   # gradio + pandas, kept out of the main deps
.venv/bin/python chat_ui.py                  # -> http://127.0.0.1:7861, simple chat tester
cd .. && backend/.venv/bin/python -m evals.eval_ui   # -> http://127.0.0.1:7860, eval dashboard
```

`chat_ui.py` calls `run_chat()` directly in the same process — no need for `uvicorn` to also be running, no auth token to manage. `evals.eval_ui` must run as a module (`-m`) from the repo root so `evals` resolves as a package; see `evals/README.md`.

## Checks

```bash
.venv/bin/pytest
.venv/bin/pytest ../evals -q   # evals package has its own tests
.venv/bin/ruff check .
.venv/bin/ruff check ../evals
.venv/bin/mypy               # no path arg — pyproject.toml's `files` covers app, tests, chat_ui.py, and ../evals;
                              # passing an explicit path (e.g. `mypy .`) overrides that config and skips evals
```

Config (LLM provider/model, embeddings model, `DATA_DIR`, Postgres, Langfuse, invite code, `FRONTEND_ORIGIN` for CORS) comes entirely from environment variables, never hardcoded — see `app/config.py` and `.env.example` at the repo root.
