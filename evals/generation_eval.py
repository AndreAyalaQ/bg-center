"""Run the full pipeline (rewrite -> retrieve -> generate) per case, then
score the answer with an LLM judge on Accuracy/Completeness/Relevance.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.pipeline import run_chat
from app.chat.turns import ChatTurn
from app.config import Settings
from app.ingest.index import MemberIndex
from evals.cases import GoldenCase, load_cases
from evals.judge import JudgeScore, judge_answer


@dataclass(frozen=True)
class CaseGenerationResult:
    case_id: str
    category: str
    question: str
    answer: str
    score: JudgeScore


@dataclass(frozen=True)
class GenerationReport:
    results: list[CaseGenerationResult]

    def _mean(self, field: str) -> float:
        values = [getattr(r.score, field) for r in self.results]
        return sum(values) / len(values) if values else 0.0

    @property
    def mean_accuracy(self) -> float:
        return self._mean("accuracy")

    @property
    def mean_completeness(self) -> float:
        return self._mean("completeness")

    @property
    def mean_relevance(self) -> float:
        return self._mean("relevance")


def run_generation_eval(
    index: MemberIndex,
    answer_settings: Settings,
    judge_settings: Settings,
    *,
    k: int = 5,
    baseline: bool = False,
    cases: list[GoldenCase] | None = None,
) -> GenerationReport:
    cases = cases if cases is not None else load_cases()
    results = []
    for case in cases:
        # Every entry in a case's `history` is a prior *user* turn (see
        # evals/sample_golden.yaml) — there's no scripted assistant reply,
        # just enough context for query rewriting to resolve "she"/"he"/etc.
        history = [ChatTurn(role="user", content=turn) for turn in case.history]
        result = run_chat(case.question, history, index, answer_settings, baseline=baseline, k=k)
        answer = "".join(result.tokens)
        score = judge_answer(case, answer, result.sources, judge_settings)
        results.append(
            CaseGenerationResult(
                case_id=case.id,
                category=case.category,
                question=case.question,
                answer=answer,
                score=score,
            )
        )
    return GenerationReport(results=results)
