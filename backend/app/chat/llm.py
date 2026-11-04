"""LLM client — OpenAI-compatible, so switching provider is a config change.

ADR-0001: Ollama locally (LLM_BASE_URL=http://localhost:11434/v1), Groq in
production, OpenRouter/Together as fallback. All four speak the same
OpenAI-compatible chat completions API.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import cast

from openai import OpenAI
from openai.types.chat import ChatCompletionChunk

from app.config import Settings

Message = dict[str, str]


@lru_cache
def _client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url or None, api_key=api_key or "not-needed")


def _client_for(settings: Settings) -> OpenAI:
    return _client(settings.llm_base_url, settings.llm_api_key)


def _extra_body(settings: Settings) -> dict[str, object] | None:
    # Ollama-only context window override — see Settings.llm_num_ctx.
    if settings.llm_num_ctx:
        return {"options": {"num_ctx": settings.llm_num_ctx}}
    return None


def stream_chat(messages: list[Message], settings: Settings) -> Iterator[str]:
    stream = _client_for(settings).chat.completions.create(
        model=settings.llm_model,
        messages=messages,  # type: ignore[arg-type]
        stream=True,
        extra_body=_extra_body(settings),
    )
    for chunk in cast(Iterator[ChatCompletionChunk], stream):
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def complete_chat(messages: list[Message], settings: Settings) -> str:
    response = _client_for(settings).chat.completions.create(
        model=settings.llm_model,
        messages=messages,  # type: ignore[arg-type]
        extra_body=_extra_body(settings),
    )
    return response.choices[0].message.content or ""
