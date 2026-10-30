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
│       ├── embeddings.py      Wraps paraphrase-multilingual-MiniLM-L12-v2 via fastembed/ONNX (ADR-0001)
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

The embeddings stack (`fastembed` + `chromadb`) installs in well under a minute, no `torch` — `.venv` lands around 600MB. (An earlier pass used `sentence-transformers` + torch, which alone cost 1.8GB; see the "Update" note in `docs/decisions/0001-llm-and-embeddings.md` for why that was dropped.) The embedding model itself (~220MB) downloads from the Hugging Face Hub on first use and is cached afterward.

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
