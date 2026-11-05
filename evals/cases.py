"""Golden case schema + loader (ADR-0005, evals/README.md § Case format)."""

from __future__ import annotations

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

EVALS_DIR = Path(__file__).resolve().parent
SAMPLE_HAND_WRITTEN = EVALS_DIR / "sample_golden.yaml"
SAMPLE_GENERATED = EVALS_DIR / "sample_golden.generated.yaml"


class GoldenCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    language: str = "en"
    history: list[str] = []
    question: str
    expected_members: list[str] = []
    expected_section: str | None = None
    must_contain: list[str] = []
    must_contain_any: list[str] = []
    must_not_contain: list[str] = []
    expect_decline: bool = False
    judge_rubric: str | None = None

    @model_validator(mode="after")
    def _has_a_way_to_grade(self) -> Self:
        has_grading = (
            self.must_contain or self.must_contain_any or self.expect_decline or self.judge_rubric
        )
        if not has_grading:
            msg = f"{self.id}: no must_contain/must_contain_any/expect_decline/judge_rubric"
            raise ValueError(msg)
        return self


def load_cases(
    hand_written: Path = SAMPLE_HAND_WRITTEN, generated: Path = SAMPLE_GENERATED
) -> list[GoldenCase]:
    """Load and merge both golden-case files — the sample track (ADR-0005)."""
    cases: list[GoldenCase] = []
    for path in (hand_written, generated):
        if not path.exists():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        cases.extend(GoldenCase.model_validate(case) for case in raw)
    return cases
