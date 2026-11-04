"""In-memory conversation + feedback storage.

Placeholder until Postgres (CLAUDE.md step 8, ADR-0002) — not durable,
lost on process restart. The point right now is a working API contract
and query-rewrite history, not persistence yet.
"""

from __future__ import annotations

import uuid

from app.chat.turns import ChatTurn


class ConversationStore:
    def __init__(self) -> None:
        self._history: dict[str, list[ChatTurn]] = {}

    def start_or_continue(self, conversation_id: str | None) -> tuple[str, list[ChatTurn]]:
        conversation_id = conversation_id or uuid.uuid4().hex
        history = self._history.setdefault(conversation_id, [])
        return conversation_id, list(history)

    def append_turn(self, conversation_id: str, user_message: str, answer: str) -> None:
        self._history[conversation_id].append(ChatTurn(role="user", content=user_message))
        self._history[conversation_id].append(ChatTurn(role="assistant", content=answer))

    def clear(self) -> None:
        self._history.clear()


class FeedbackRecord:
    def __init__(self, message_id: str, rating: str, comment: str | None) -> None:
        self.message_id = message_id
        self.rating = rating
        self.comment = comment


class FeedbackStore:
    def __init__(self) -> None:
        self._records: list[FeedbackRecord] = []

    def record(self, message_id: str, rating: str, comment: str | None) -> None:
        self._records.append(FeedbackRecord(message_id, rating, comment))

    def clear(self) -> None:
        self._records.clear()
