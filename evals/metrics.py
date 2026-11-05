"""Retrieval-quality metrics: Mean Reciprocal Rank, nDCG, keyword coverage.

Binary relevance: a retrieved chunk is relevant if its `member` is in the
case's `expected_members` — matches the recall@k definition already used
elsewhere in the project (evals/README.md), no new eval-case fields needed.

nDCG is computed against the ideal ordering of the *retrieved* set itself
(not the full corpus) — the golden cases give a relevant/not-relevant
member list, not a ranked judgment over every chunk in the index, so the
practical ideal is "the same chunks, optimally ordered."

Cases with no ground truth for a metric (`expected_members: []` for
MRR/nDCG, no must_contain/must_contain_any for keyword coverage — both
genuine cases in the adversarial/injection categories) return None and
are excluded from aggregates, not scored as 0.
"""

from __future__ import annotations

import math
import unicodedata

from app.ingest.index import RetrievedChunk
from evals.cases import GoldenCase


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _contains(haystack: str, needle: str) -> bool:
    return _normalize(needle) in _normalize(haystack)


def reciprocal_rank(retrieved: list[RetrievedChunk], case: GoldenCase) -> float | None:
    expected = set(case.expected_members)
    if not expected:
        return None
    for rank, chunk in enumerate(retrieved, start=1):
        if chunk.member in expected:
            return 1 / rank
    return 0.0


def ndcg(retrieved: list[RetrievedChunk], case: GoldenCase) -> float | None:
    expected = set(case.expected_members)
    if not expected:
        return None
    if not retrieved:
        return 0.0

    relevances = [1 if chunk.member in expected else 0 for chunk in retrieved]

    def dcg(values: list[int]) -> float:
        return sum(rel / math.log2(i + 2) for i, rel in enumerate(values))

    ideal = dcg(sorted(relevances, reverse=True))
    return dcg(relevances) / ideal if ideal > 0 else 0.0


def keyword_coverage(retrieved: list[RetrievedChunk], case: GoldenCase) -> float | None:
    """Fraction of the case's required keywords found in the retrieved chunk text.

    Every `must_contain` entry is individually required; `must_contain_any`
    counts as a single satisfied unit if any one of its options is found.
    """
    required = len(case.must_contain) + (1 if case.must_contain_any else 0)
    if required == 0:
        return None

    haystack = "\n".join(chunk.text for chunk in retrieved)
    satisfied = sum(1 for kw in case.must_contain if _contains(haystack, kw))
    if case.must_contain_any and any(_contains(haystack, kw) for kw in case.must_contain_any):
        satisfied += 1
    return satisfied / required
