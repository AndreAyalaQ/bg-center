"""Query rewrite: fold conversation history into a standalone question.

docs/design.md § Architecture: "last 4 turns -> standalone question", so a
follow-up like "And what does he do?" can be retrieved on its own. Skipped
entirely when there's no history — the first turn's message is already
standalone, and skipping avoids a pointless extra LLM round trip.
"""

from __future__ import annotations

from app.chat.llm import complete_chat
from app.chat.turns import ChatTurn
from app.config import Settings

HISTORY_WINDOW = 4

_SYSTEM_PROMPT = (
    "Rewrite the user's latest message as a standalone question that makes "
    "sense without the earlier conversation, resolving pronouns and implicit "
    "references using the conversation history below. Keep the same language "
    "as the latest message. Reply with only the rewritten question, nothing else."
)


def rewrite_query(message: str, history: list[ChatTurn], settings: Settings) -> str:
    if not history:
        return message

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages += [{"role": turn.role, "content": turn.content} for turn in history[-HISTORY_WINDOW:]]
    messages.append({"role": "user", "content": message})

    rewritten = complete_chat(messages, settings).strip()
    return rewritten or message
