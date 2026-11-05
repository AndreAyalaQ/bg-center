from evals.eval_ui import _generation_chart
from evals.generation_eval import CaseGenerationResult, GenerationReport
from evals.judge import JudgeScore


def _result(accuracy: int, completeness: int, relevance: int) -> CaseGenerationResult:
    score = JudgeScore(
        accuracy=accuracy, completeness=completeness, relevance=relevance, reasoning=""
    )
    return CaseGenerationResult(
        case_id="t",
        category="single_fact",
        question="q?",
        answer="a",
        score=score,
    )


def test_generation_chart_uses_real_scores_when_not_all_zero() -> None:
    report = GenerationReport(results=[_result(4, 5, 3)])
    chart = _generation_chart(report)
    assert chart["score"].tolist() == [4.0, 5.0, 3.0]


def test_generation_chart_nudges_all_zero_scores_above_zero() -> None:
    # Gradio/Vega-Lite renders a bar chart where every value is exactly 0
    # as full-height bars with a degenerate single-tick axis instead of
    # empty bars on the 0-5 scale — confirmed by direct browser testing.
    # The chart must show a tiny positive value instead, not literal 0.0.
    report = GenerationReport(results=[_result(0, 0, 0)])
    chart = _generation_chart(report)
    assert all(score > 0 for score in chart["score"])
    assert all(score < 0.01 for score in chart["score"])


def test_generation_chart_with_no_results_also_avoids_the_degenerate_case() -> None:
    report = GenerationReport(results=[])
    chart = _generation_chart(report)
    assert all(score > 0 for score in chart["score"])
