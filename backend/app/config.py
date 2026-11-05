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
    # Ollama-specific context window override. 0 = unset, use the
    # provider's default. Needed locally: Ollama's default 4096-token
    # context can be exhausted by a thinking-enabled model's internal
    # reasoning before it produces a visible answer — see the "Update"
    # note in docs/decisions/0001-llm-and-embeddings.md. Hosted providers
    # (Groq etc.) size their own context and ignore/ don't need this.
    llm_num_ctx: int = 0
    # Request timeout for the OpenAI-compatible client. The SDK's own
    # default (600s) is too short for a thinking-enabled model on local
    # CPU-only Ollama — observed single calls taking 20-40+ minutes this
    # session, which raised openai.APITimeoutError. 600 matches the SDK
    # default so hosted providers (Groq etc.) are unaffected unless raised.
    llm_timeout_seconds: float = 600

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
