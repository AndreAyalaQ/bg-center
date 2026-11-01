from app.chat.prompt import build_messages
from app.chat.turns import ChatTurn
from app.ingest.index import RetrievedChunk


def _chunk(text: str = "João (Jota) – Facts: lives in Lisboa.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="joao-facts",
        text=text,
        member="joao",
        section="facts",
        source_file="joao.md",
        score=0.9,
    )


def test_system_prompt_includes_context_and_decline_instruction() -> None:
    messages = build_messages("Where does Jota live?", [], [_chunk()])
    system = messages[0]
    assert system["role"] == "system"
    assert "lives in Lisboa" in system["content"]
    assert "don't know" in system["content"]
    assert "Não sei" in system["content"]


def test_system_prompt_warns_against_instructions_hidden_in_context() -> None:
    messages = build_messages("q", [], [_chunk()])
    assert "never instructions" in messages[0]["content"] or "data, never" in messages[0]["content"]


def test_empty_context_uses_placeholder_not_empty_string() -> None:
    messages = build_messages("Where does Jota live?", [], [])
    assert "no matching member information" in messages[0]["content"]


def test_history_is_included_after_system_before_question() -> None:
    history = [
        ChatTurn(role="user", content="Who is the oldest in the group?"),
        ChatTurn(role="assistant", content="João is the oldest."),
    ]
    messages = build_messages("And what does he do?", history, [_chunk()])
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"] == "And what does he do?"


def test_only_the_last_four_history_turns_are_kept() -> None:
    history = [
        ChatTurn(role="user" if i % 2 == 0 else "assistant", content=f"turn {i}") for i in range(10)
    ]
    messages = build_messages("latest", history, [])
    history_messages = messages[1:-1]
    assert len(history_messages) == 4
    assert [m["content"] for m in history_messages] == ["turn 6", "turn 7", "turn 8", "turn 9"]
