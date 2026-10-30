# backend

FastAPI app and RAG pipeline. Ingestion (parse → chunk → embed → index) is built; the chat pipeline (query rewrite, retrieval, grounded generation) and the API endpoints are not yet — see `docs/design.md` and the root `CLAUDE.md` build plan (steps 4–5).

## Layout

```
backend/
├── app/
│   ├── main.py            FastAPI app, CORS, /health; builds the member index at startup
│   ├── config.py           Settings loaded from the environment (ADR-0001)
│   └── ingest/
│       ├── parser.py        Markdown + YAML frontmatter → Member/Section (ADR-0004)
│       ├── chunker.py        Member -> embeddable Chunks, incl. the synthesized facts chunk
│       ├── embeddings.py      Wraps intfloat/multilingual-e5-small, CPU-only (ADR-0001)
│       └── index.py           In-memory Chroma collection, built at startup
├── tests/
└── pyproject.toml
```

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example ../.env   # fill in values; loaded from the repo root
```

The embeddings stack (`sentence-transformers` + CPU-only `torch` + `chromadb`) is a real install — expect roughly 1–2GB of downloads and disk, and the CPU build of torch specifically (`--extra-index-url https://download.pytorch.org/whl/cpu`) to avoid pulling in CUDA. The embedding model itself (~470MB) downloads from the Hugging Face Hub on first use and is cached afterward.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
# -> GET http://127.0.0.1:8000/health
# {"status":"ok","environment":"development","indexed_chunks":31}
```

`indexed_chunks` confirms the startup ingestion actually ran: parse `DATA_DIR` → chunk → embed → build the in-memory index.

## Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy .
```

Config (LLM provider/model, embeddings model, `DATA_DIR`, Postgres, Langfuse, invite code, `FRONTEND_ORIGIN` for CORS) comes entirely from environment variables, never hardcoded — see `app/config.py` and `.env.example` at the repo root.
