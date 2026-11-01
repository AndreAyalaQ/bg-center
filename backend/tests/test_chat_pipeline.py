from pathlib import Path

import pytest

from app.chat import pipeline as pipeline_module
from app.chat.pipeline import run_chat
from app.config import Settings
from app.ingest.index import MemberIndex

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "members"


@pytest.fixture(scope="module")
def index() -> MemberIndex:
    return MemberIndex(SAMPLE_DIR)


@pytest.fixture(autouse=True)
def _stub_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    # No history in these tests, so rewrite_query already short-circuits
    # without calling the LLM (see test_chat_rewrite.py) — only the
    # generation call needs stubbing here.
    monkeypatch.setattr(pipeline_module, "stream_chat", lambda messages, settings: iter(["token"]))


def test_run_chat_retrieves_top_k_by_default(index: MemberIndex) -> None:
    result = run_chat("Where does Jota live?", [], index, Settings(), k=3)
    assert result.standalone_question == "Where does Jota live?"
    assert len(result.sources) == 3
    assert result.sources[0].member == "joao"
    assert list(result.tokens) == ["token"]


def test_run_chat_baseline_stuffs_every_chunk(index: MemberIndex) -> None:
    result = run_chat("Where does Jota live?", [], index, Settings(), baseline=True)
    assert len(result.sources) == index.size


def test_run_chat_passes_sources_into_the_prompt(
    index: MemberIndex, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, str]] = []

    def capture(messages: list[dict[str, str]], settings: Settings) -> object:
        captured.extend(messages)
        return iter(["token"])

    monkeypatch.setattr(pipeline_module, "stream_chat", capture)
    run_chat("Where does Jota live?", [], index, Settings(), k=1)
    assert "Lisboa" in captured[0]["content"]
