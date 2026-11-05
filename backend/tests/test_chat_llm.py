from app.chat.llm import _client_for
from app.config import Settings


def test_client_uses_configured_timeout() -> None:
    settings = Settings(llm_timeout_seconds=1800)
    client = _client_for(settings)
    assert client.timeout == 1800


def test_client_defaults_to_sdk_timeout_when_unset() -> None:
    # _env_file=None: don't let the ambient .env (which may itself set
    # LLM_TIMEOUT_SECONDS for local Ollama work) mask the field default.
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    client = _client_for(settings)
    assert client.timeout == 600
