import pytest

from app.chat import rewrite as rewrite_module
from app.chat.rewrite import rewrite_query
from app.chat.turns import ChatTurn
from app.config import Settings


def test_rewrite_skips_llm_call_when_there_is_no_history(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> str:
        raise AssertionError("complete_chat should not be called with no history")

    monkeypatch.setattr(rewrite_module, "complete_chat", fail_if_called)
    result = rewrite_query("Where does Jota live?", [], Settings())
    assert result == "Where does Jota live?"


def test_rewrite_uses_llm_output_when_history_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_complete(messages: list[dict[str, str]], settings: Settings) -> str:
        return "What does João do?"

    monkeypatch.setattr(rewrite_module, "complete_chat", fake_complete)
    history = [
        ChatTurn(role="user", content="Who is the oldest in the group?"),
        ChatTurn(role="assistant", content="João is."),
    ]
    result = rewrite_query("And what does he do?", history, Settings())
    assert result == "What does João do?"


def test_rewrite_falls_back_to_original_message_on_blank_llm_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rewrite_module, "complete_chat", lambda messages, settings: "   ")
    history = [ChatTurn(role="user", content="prior turn")]
    result = rewrite_query("follow-up", history, Settings())
    assert result == "follow-up"


def test_rewrite_only_sends_the_last_four_history_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, str]] = []

    def capture(messages: list[dict[str, str]], settings: Settings) -> str:
        captured.extend(messages)
        return "rewritten"

    monkeypatch.setattr(rewrite_module, "complete_chat", capture)
    history = [
        ChatTurn(role="user" if i % 2 == 0 else "assistant", content=f"turn {i}") for i in range(10)
    ]
    rewrite_query("latest", history, Settings())

    # system prompt + 4 history turns + the latest message
    history_messages = captured[1:-1]
    assert [m["content"] for m in history_messages] == ["turn 6", "turn 7", "turn 8", "turn 9"]
