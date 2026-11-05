import pytest
from pydantic import ValidationError

from evals.cases import GoldenCase, load_cases


def test_case_requires_a_way_to_grade() -> None:
    with pytest.raises(ValidationError, match="no must_contain"):
        GoldenCase.model_validate({"id": "x", "category": "single_fact", "question": "q?"})


def test_case_accepts_expect_decline_alone() -> None:
    case = GoldenCase.model_validate(
        {"id": "x", "category": "unanswerable", "question": "q?", "expect_decline": True}
    )
    assert case.expect_decline


def test_load_cases_merges_hand_written_and_generated() -> None:
    cases = load_cases()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids across the two files"
    assert "story-porto-en" in ids  # hand-written
    assert "fact-city-joao" in ids  # generated
    assert len(cases) > 50


def test_load_cases_all_have_a_category_and_language() -> None:
    for case in load_cases():
        assert case.category
        assert case.language in {"en", "pt"}
