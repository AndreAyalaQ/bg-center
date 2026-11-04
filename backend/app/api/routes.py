"""API routes (docs/design.md § API contract)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.api.auth import issue_token, require_token
from app.api.schemas import (
    AuthRequest,
    AuthResponse,
    ChatDoneEvent,
    ChatRequest,
    FeedbackRequest,
    MemberOut,
    SourceOut,
)
from app.api.store import ConversationStore, FeedbackStore
from app.chat.pipeline import run_chat
from app.config import Settings, get_settings
from app.ingest.index import MemberIndex

router = APIRouter(prefix="/api")

# Module-level: one process, one in-memory store (see app/api/store.py).
conversation_store = ConversationStore()
feedback_store = FeedbackStore()


@router.post("/auth", response_model=AuthResponse)
def auth(body: AuthRequest, settings: Settings = Depends(get_settings)) -> AuthResponse:
    if not settings.invite_code or body.invite_code != settings.invite_code:
        raise HTTPException(status_code=401, detail="Invalid invite code")
    return AuthResponse(token=issue_token(settings))


@router.get("/members", response_model=list[MemberOut], dependencies=[Depends(require_token)])
def list_members(request: Request) -> list[MemberOut]:
    index: MemberIndex = request.app.state.member_index
    return [
        MemberOut(
            id=member.id,
            name=str(member.meta.get("name", member.id)),
            nickname=member.meta.get("nickname"),
            avatar_url=member.meta.get("avatar_url"),
            tagline=member.meta.get("tagline"),
        )
        for member in index.members
    ]


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat", dependencies=[Depends(require_token)])
def chat(
    body: ChatRequest, request: Request, settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    index: MemberIndex = request.app.state.member_index
    conversation_id, history = conversation_store.start_or_continue(body.conversation_id)

    # A plain (sync) generator — Starlette runs it via iterate_in_threadpool
    # since app/chat/llm.py's stream_chat is itself a blocking generator,
    # so this doesn't block the event loop for other requests.
    def event_stream() -> Iterator[str]:
        result = run_chat(body.message, history, index, settings)
        answer_parts: list[str] = []
        for token in result.tokens:
            answer_parts.append(token)
            yield _sse("token", {"token": token})

        answer = "".join(answer_parts)
        conversation_store.append_turn(conversation_id, body.message, answer)

        done = ChatDoneEvent(
            conversation_id=conversation_id,
            message_id=uuid.uuid4().hex,
            sources=[
                SourceOut(member=s.member, section=s.section, snippet=s.text[:200])
                for s in result.sources
            ],
        )
        yield _sse("done", done.model_dump(by_alias=True))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/feedback", status_code=204, dependencies=[Depends(require_token)])
def feedback(body: FeedbackRequest) -> Response:
    feedback_store.record(body.message_id, body.rating, body.comment)
    return Response(status_code=204)
