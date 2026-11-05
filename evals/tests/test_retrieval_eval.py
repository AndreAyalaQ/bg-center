from pathlib import Path

import pytest

from app.config import Settings
from app.ingest.index import MemberIndex
from evals import retrieval_eval as retrieval_eval_module
from evals.cases import GoldenCase
from evals.retrieval_eval import run_retrieval_eval

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "members"


@pytest.fixture(scope="module")
def index() -> MemberIndex:
    return MemberIndex(SAMPLE_DIR)


def test_follow_up_case_uses_raw_question_without_settings(index: MemberIndex) -> None:
    case = GoldenCase.model_validate(
        {
            "id": "t",
            "category": "follow_up",
            "history": ["Who is the tallest?"],
            "question": "And where does he live?",
            "expected_members": ["tomas"],
            "must_contain": ["Lisboa"],
        }
    )
    report = run_retrieval_eval(index, k=3, cases=[case])
    assert report.results[0].standalone_question == "And where does he live?"


def test_follow_up_case_is_rewritten_when_settings_given(
    index: MemberIndex, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_rewrite(message: str, history: list[object], settings: object) -> str:
        return "Where does Tomás live?"

    monkeypatch.setattr(retrieval_eval_module, "rewrite_query", fake_rewrite)
    case = GoldenCase.model_validate(
        {
            "id": "t",
            "category": "follow_up",
            "history": ["Who is the tallest?"],
            "question": "And where does he live?",
            "expected_members": ["tomas"],
            "must_contain": ["Lisboa"],
        }
    )
    report = run_retrieval_eval(index, k=3, cases=[case], settings=Settings())
    assert report.results[0].standalone_question == "Where does Tomás live?"
    assert report.results[0].reciprocal_rank == 1.0


def test_case_without_history_is_unaffected_by_settings(
    index: MemberIndex, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_called(message: str, history: list[object], settings: object) -> str:
        raise AssertionError("rewrite_query should not be called without history")

    monkeypatch.setattr(retrieval_eval_module, "rewrite_query", fail_if_called)
    case = GoldenCase.model_validate(
        {
            "id": "t",
            "category": "single_fact",
            "question": "Where does Tomás live?",
            "expected_members": ["tomas"],
            "must_contain": ["Lisboa"],
        }
    )
    report = run_retrieval_eval(index, k=3, cases=[case], settings=Settings())
    assert report.results[0].standalone_question == "Where does Tomás live?"
