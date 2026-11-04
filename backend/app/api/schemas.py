"""Request/response schemas (docs/design.md § API contract).

pydantic `BaseModel`s per CLAUDE.md step 5 — idiomatic FastAPI, gives
validation and OpenAPI schema generation for free. Field names are
snake_case internally; the wire format is camelCase (`inviteCode`,
`conversationId`, ...), handled by a shared alias generator rather than
hand-writing an alias per field.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AuthRequest(CamelModel):
    invite_code: str


class AuthResponse(CamelModel):
    token: str


class MemberOut(CamelModel):
    id: str
    name: str
    nickname: str | None = None
    avatar_url: str | None = None
    tagline: str | None = None


class ChatRequest(CamelModel):
    message: str
    conversation_id: str | None = None


class SourceOut(CamelModel):
    member: str
    section: str
    snippet: str


class ChatDoneEvent(CamelModel):
    conversation_id: str
    message_id: str
    sources: list[SourceOut]


class FeedbackRequest(CamelModel):
    message_id: str
    rating: Literal["up", "down"]
    comment: str | None = None
