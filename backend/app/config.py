"""App configuration, loaded entirely from the environment.

Model name, base URL, and all secrets live in config (.env locally, the
hosting platform's environment variables in production) per ADR-0001 —
never hardcoded, since provider catalogs and model choices change.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root (see .env.example there), not in backend/ —
# resolved relative to this file rather than the process's cwd, since
# uvicorn is normally launched from inside backend/.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM provider (ADR-0001)
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    judge_llm_model: str = ""

    # Embeddings (ADR-0001)
    embeddings_model: str = ""

    # Data (ADR-0003, ADR-0004)
    data_dir: str = "data/sample/members"

    # Postgres (ADR-0002)
    database_url: str = ""

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Access control (docs/design.md § Privacy and safety)
    invite_code: str = ""
    jwt_secret: str = ""

    # CORS — the frontend origin only, per docs/design.md § API contract
    frontend_origin: str = "http://localhost:5173"

    environment: str = Field(default="development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
