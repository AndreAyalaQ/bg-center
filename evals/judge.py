"""LLM-as-judge scoring: Accuracy, Completeness, Relevance, 0-5 each.

A different, stronger model than the one answering (ADR-0001) — the judge
model comes from JUDGE_LLM_MODEL and isn't swappable from the eval UI's
answering-model picker, so scores stay comparable across runs that vary
the answering model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.chat.llm import complete_chat
from app.config import Settings
from app.ingest.index import RetrievedChunk
from evals.cases import GoldenCase

_SYSTEM_PROMPT = """You are grading an AI assistant's answer to a question about members of \
a friend group, in a RAG chat system. Score strictly and consistently across cases.

You will be given the question, the member-profile text retrieved as context (the ground \
truth — not the assistant's own knowledge), the assistant's answer, and optionally a rubric \
describing what a correct answer looks like, or a note that the expected answer is a decline \
because the context doesn't contain the answer.

Score the answer 0-5 on each dimension:

- accuracy: Is the answer factually correct according to the retrieved context? 5 = every \
claim is correct and grounded in the context (or, for an expected-decline case, the answer \
correctly declines instead of inventing something). 0 = the answer states something false, \
contradicted by the context, or invented.
- completeness: Does the answer cover all the aspects of the question and all the relevant \
information available in the context/rubric? 5 = nothing relevant is missing. 0 = misses most \
or all of the relevant information.
- relevance: Does the answer directly address the specific question asked, without padding or \
unrelated information? 5 = answers exactly what was asked, concisely, with no extra \
information. 0 = answers a different question or buries the answer in irrelevant content.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"accuracy": <0-5 integer>, "completeness": <0-5 integer>, "relevance": <0-5 integer>, \
"reasoning": "<one sentence>"}"""


@dataclass(frozen=True)
class JudgeScore:
    accuracy: int
    completeness: int
    relevance: int
    reasoning: str


def _render_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no context was retrieved)"
    return "\n\n---\n\n".join(chunk.text for chunk in chunks)


def _build_user_message(case: GoldenCase, answer: str, context_chunks: list[RetrievedChunk]) -> str:
    parts = [
        f"Question: {case.question}",
        f"Context:\n{_render_context(context_chunks)}",
        f"Assistant's answer: {answer}",
    ]
    if case.judge_rubric:
        parts.append(f"Rubric: {case.judge_rubric}")
    if case.expect_decline:
        parts.append("Note: the context does not contain the answer — a correct response declines.")
    return "\n\n".join(parts)


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _clamp_0_to_5(value: int | float | str) -> int:
    return max(0, min(5, int(value)))


def _parse_score(raw: str) -> JudgeScore:
    match = _JSON_RE.search(raw)
    if not match:
        raise ValueError(f"judge did not return JSON: {raw!r}")
    data = json.loads(match.group(0))
    return JudgeScore(
        accuracy=_clamp_0_to_5(data["accuracy"]),
        completeness=_clamp_0_to_5(data["completeness"]),
        relevance=_clamp_0_to_5(data["relevance"]),
        reasoning=str(data.get("reasoning", "")),
    )


def judge_answer(
    case: GoldenCase,
    answer: str,
    context_chunks: list[RetrievedChunk],
    judge_settings: Settings,
) -> JudgeScore:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(case, answer, context_chunks)},
    ]
    raw = complete_chat(messages, judge_settings)
    return _parse_score(raw)
