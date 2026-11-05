"""Run the retrieval-only metrics (MRR, nDCG, keyword coverage) across the golden set.

Mostly LLM-free — just embeddings + vector search (ADR-0005's "cheapest
first" philosophy) — with one deliberate exception: a `follow_up` case's
`question` is a raw fragment ("And what does he do?") that was never meant
to be retrieved on its own; the real pipeline always rewrites it to a
standalone question first (app/chat/rewrite.py). Skipping that step here
would make follow-up retrieval look artificially weak for a reason that
has nothing to do with retrieval — so when `settings` is given, history-
bearing cases are rewritten with the *same* model being evaluated before
querying, matching production and making the numbers comparable across
models (a model whose rewrites are bad hurts its own retrieval score here,
which is the correct signal). Without `settings`, these cases fall back to
the raw fragment — degraded but LLM-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.rewrite import rewrite_query
from app.chat.turns import ChatTurn
from app.config import Settings
from app.ingest.index import MemberIndex
from evals.cases import GoldenCase, load_cases
from evals.metrics import keyword_coverage, ndcg, reciprocal_rank


@dataclass(frozen=True)
class CaseRetrievalResult:
    case_id: str
    category: str
    question: str
    standalone_question: str  # == question unless rewritten from history
    reciprocal_rank: float | None
    ndcg: float | None
    keyword_coverage: float | None


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


@dataclass(frozen=True)
class RetrievalReport:
    k: int
    results: list[CaseRetrievalResult]

    @property
    def mean_reciprocal_rank(self) -> float | None:
        return _mean([r.reciprocal_rank for r in self.results])

    @property
    def mean_ndcg(self) -> float | None:
        return _mean([r.ndcg for r in self.results])

    @property
    def mean_keyword_coverage(self) -> float | None:
        return _mean([r.keyword_coverage for r in self.results])


def run_retrieval_eval(
    index: MemberIndex,
    k: int = 5,
    cases: list[GoldenCase] | None = None,
    settings: Settings | None = None,
) -> RetrievalReport:
    cases = cases if cases is not None else load_cases()
    results = []
    for case in cases:
        standalone_question = case.question
        if case.history and settings is not None:
            history = [ChatTurn(role="user", content=turn) for turn in case.history]
            standalone_question = rewrite_query(case.question, history, settings)

        retrieved = index.query(standalone_question, k=k)
        results.append(
            CaseRetrievalResult(
                case_id=case.id,
                category=case.category,
                question=case.question,
                standalone_question=standalone_question,
                reciprocal_rank=reciprocal_rank(retrieved, case),
                ndcg=ndcg(retrieved, case),
                keyword_coverage=keyword_coverage(retrieved, case),
            )
        )
    return RetrievalReport(k=k, results=results)
