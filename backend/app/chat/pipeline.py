"""Chat pipeline: rewrite -> retrieve (or stuff-everything baseline) -> stream a grounded answer.

docs/design.md § Architecture, ADR-0005 (stuff-everything baseline, compared
from day one against RAG at k = 3, 5, 8).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app.chat.llm import stream_chat
from app.chat.prompt import build_messages
from app.chat.rewrite import rewrite_query
from app.chat.turns import ChatTurn
from app.config import Settings
from app.ingest.index import MemberIndex, RetrievedChunk

DEFAULT_K = 5


@dataclass
class ChatResult:
    standalone_question: str
    sources: list[RetrievedChunk]
    tokens: Iterator[str]


def run_chat(
    message: str,
    history: list[ChatTurn],
    index: MemberIndex,
    settings: Settings,
    *,
    baseline: bool = False,
    k: int = DEFAULT_K,
) -> ChatResult:
    standalone_question = rewrite_query(message, history, settings)
    sources = index.all_chunks() if baseline else index.query(standalone_question, k=k)
    messages = build_messages(standalone_question, history, sources)
    tokens = stream_chat(messages, settings)
    return ChatResult(standalone_question=standalone_question, sources=sources, tokens=tokens)
