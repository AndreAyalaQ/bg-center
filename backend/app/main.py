from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import get_settings
from app.ingest.embeddings import DEFAULT_MODEL
from app.ingest.index import MemberIndex

settings = get_settings()

# Resolved relative to the repo root (backend/ and data/ are siblings),
# matching DATA_DIR in .env.example.
REPO_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    data_dir = Path(settings.data_dir)
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir
    # Model name lives in config, never hardcoded (ADR-0001) — DEFAULT_MODEL
    # is only the fallback for an unset EMBEDDINGS_MODEL.
    model_name = settings.embeddings_model or DEFAULT_MODEL
    app.state.member_index = MemberIndex(data_dir, model_name=model_name)
    yield


app = FastAPI(title="BG Center backend", lifespan=lifespan)

# CORS allows the frontend origin only, configured from day one
# (docs/design.md § API contract).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "indexed_chunks": app.state.member_index.size,
    }
