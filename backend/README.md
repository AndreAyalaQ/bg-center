# backend

FastAPI app and RAG pipeline. Currently a skeleton: config loading and a health check. The RAG pipeline itself is not yet implemented — see `docs/design.md` and the root `CLAUDE.md` build plan (steps 3–5).

## Layout

```
backend/
├── app/
│   ├── main.py      FastAPI app, CORS, /health
│   └── config.py    Settings loaded from the environment (ADR-0001)
├── tests/
│   └── test_health.py
└── pyproject.toml
```

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example ../.env   # fill in values; loaded from the repo root
```

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
# -> GET http://127.0.0.1:8000/health
```

## Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy .
```

Config (LLM provider/model, embeddings model, `DATA_DIR`, Postgres, Langfuse, invite code, `FRONTEND_ORIGIN` for CORS) comes entirely from environment variables, never hardcoded — see `app/config.py` and `.env.example` at the repo root.
