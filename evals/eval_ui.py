"""Gradio dashboard: retrieval-quality metrics + LLM-judge generation quality.

Run with (from the repo root — needs `-m` so `evals` resolves as a package):
    backend/.venv/bin/python -m evals.eval_ui

Two tabs:
- Retrieval quality: MRR, nDCG, keyword coverage over the sample golden set
  (evals/sample_golden.yaml + evals/sample_golden.generated.yaml), no LLM
  generation involved (history-bearing cases are rewritten with the
  answering model first — see evals/retrieval_eval.py's docstring).
- Generation quality: runs the full chat pipeline per case, then an LLM
  judge scores Accuracy/Completeness/Relevance 0-5 each (ADR-0001: a
  different, stronger judge model than the one answering).

Color thresholds (as specified): MRR/nDCG — red <=0.73, yellow <0.85,
green >=0.85. Keyword coverage — red <70%, yellow <85%, green >=85%.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import gradio as gr
import pandas as pd

from app.config import Settings
from app.ingest.index import MemberIndex
from evals.cases import load_cases
from evals.generation_eval import GenerationReport, run_generation_eval
from evals.retrieval_eval import RetrievalReport, run_retrieval_eval

_REPO_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_SETTINGS = Settings()
_data_dir = Path(_DEFAULT_SETTINGS.data_dir)
if not _data_dir.is_absolute():
    _data_dir = _REPO_ROOT / _data_dir
_INDEX = MemberIndex(_data_dir)
_CASES = load_cases()

_MODEL_PRESETS: dict[str, tuple[str, str]] = {
    "Default (.env)": (_DEFAULT_SETTINGS.llm_base_url, _DEFAULT_SETTINGS.llm_model),
    "Ollama (local): qwen3.5:9b": ("http://localhost:11434/v1", "qwen3.5:9b"),
    "Groq (hosted): llama-3.3-70b-versatile": (
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
    ),
}


def _answer_settings(preset: str, model_override: str, api_key_override: str) -> Settings:
    base_url, default_model = _MODEL_PRESETS.get(preset, _MODEL_PRESETS["Default (.env)"])
    return Settings(
        llm_base_url=base_url,
        llm_model=model_override.strip() or default_model,
        llm_api_key=api_key_override.strip() or _DEFAULT_SETTINGS.llm_api_key,
        llm_num_ctx=_DEFAULT_SETTINGS.llm_num_ctx,
        llm_timeout_seconds=_DEFAULT_SETTINGS.llm_timeout_seconds,
    )


# --- colored badges --------------------------------------------------------


def _badge(
    label: str, value: float | None, red_max: float, yellow_max: float, as_percent: bool
) -> str:
    if value is None:
        return f"<div style='padding:8px'><b>{label}</b>: n/a</div>"
    color = "#d93025" if value <= red_max else ("#f29900" if value < yellow_max else "#188038")
    text = f"{value:.0%}" if as_percent else f"{value:.3f}"
    return (
        f"<div style='padding:12px;border-radius:8px;background:{color};color:white;"
        f"text-align:center;min-width:140px'><div style='font-size:13px'>{label}</div>"
        f"<div style='font-size:28px;font-weight:bold'>{text}</div></div>"
    )


def _retrieval_badges(report: RetrievalReport) -> str:
    mrr = _badge("Mean Reciprocal Rank", report.mean_reciprocal_rank, 0.73, 0.85, as_percent=False)
    nd = _badge("nDCG", report.mean_ndcg, 0.73, 0.85, as_percent=False)
    cov = _badge("Keyword Coverage", report.mean_keyword_coverage, 0.70, 0.85, as_percent=True)
    return f"<div style='display:flex;gap:16px'>{mrr}{nd}{cov}</div>"


def _retrieval_table(report: RetrievalReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": r.case_id,
                "category": r.category,
                "question": r.question,
                "rewritten": r.standalone_question if r.standalone_question != r.question else "",
                "MRR": r.reciprocal_rank,
                "nDCG": r.ndcg,
                "coverage": r.keyword_coverage,
            }
            for r in report.results
        ]
    )


def run_retrieval_panel(
    preset: str, model_override: str, api_key_override: str, k: int, use_rewrite: bool
) -> tuple[str, pd.DataFrame]:
    settings = _answer_settings(preset, model_override, api_key_override) if use_rewrite else None
    report = run_retrieval_eval(_INDEX, k=int(k), cases=_CASES, settings=settings)
    return _retrieval_badges(report), _retrieval_table(report)


# --- generation quality --------------------------------------------------------


def _generation_chart(report: GenerationReport) -> pd.DataFrame:
    scores = [report.mean_accuracy, report.mean_completeness, report.mean_relevance]
    if all(s == 0 for s in scores):
        # Gradio/Vega-Lite edge case, confirmed by direct testing: a bar
        # chart where every value is exactly 0 renders as full-height bars
        # with a degenerate single-tick ("0") axis instead of empty bars on
        # a 0-5 scale — any other all-equal value (e.g. all 3.0) renders
        # correctly, so this is specifically about zero, not y_lim in
        # general. Nudging to a tiny epsilon keeps the bars visually empty
        # (indistinguishable from true 0 at this scale) while avoiding the
        # degenerate-domain rendering path. Table values are unaffected.
        scores = [1e-6, 1e-6, 1e-6]
    return pd.DataFrame({"dimension": ["Accuracy", "Completeness", "Relevance"], "score": scores})


def _generation_table(report: GenerationReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": r.case_id,
                "category": r.category,
                "question": r.question,
                "answer": r.answer,
                "accuracy": r.score.accuracy,
                "completeness": r.score.completeness,
                "relevance": r.score.relevance,
                "reasoning": r.score.reasoning,
            }
            for r in report.results
        ]
    )


def run_generation_panel(
    preset: str,
    model_override: str,
    api_key_override: str,
    k: int,
    baseline: bool,
    categories: list[str],
    limit: int,
    progress: gr.Progress = gr.Progress(),
) -> Iterator[tuple[pd.DataFrame, pd.DataFrame, str]]:
    answer_settings = _answer_settings(preset, model_override, api_key_override)
    judge_settings = _DEFAULT_SETTINGS

    cases = [c for c in _CASES if not categories or c.category in categories]
    if limit:
        cases = cases[: int(limit)]
    if not cases:
        yield pd.DataFrame(), pd.DataFrame(), "No cases match the selected categories."
        return

    yield pd.DataFrame(), pd.DataFrame(), f"Running {len(cases)} case(s)…"

    results = []
    for i, case in enumerate(cases):
        progress((i, len(cases)), desc=f"{case.id} ({i + 1}/{len(cases)})")
        report = run_generation_eval(
            _INDEX, answer_settings, judge_settings, k=int(k), baseline=baseline, cases=[case]
        )
        results.extend(report.results)
        running = GenerationReport(results=results)
        status = f"{i + 1}/{len(cases)} done — last: {case.id}"
        yield _generation_chart(running), _generation_table(running), status

    yield _generation_chart(GenerationReport(results=results)), _generation_table(
        GenerationReport(results=results)
    ), f"Done — {len(results)} case(s) scored."


# --- UI --------------------------------------------------------------


_ALL_CATEGORIES = sorted({c.category for c in _CASES})


def build_app() -> gr.Blocks:
    with gr.Blocks(title="BG Center — Eval Dashboard") as app:
        gr.Markdown(
            "# BG Center eval dashboard\nSample track only (ADR-0005) — never real friend data."
        )

        with gr.Row():
            preset = gr.Dropdown(
                list(_MODEL_PRESETS), value="Default (.env)", label="Answering model preset"
            )
            model_override = gr.Textbox(label="Model override (optional)")
            api_key_override = gr.Textbox(label="API key override (optional)", type="password")

        with gr.Tab("Retrieval quality"):
            gr.Markdown(
                "MRR & nDCG: red ≤0.73, yellow <0.85, green ≥0.85. "
                "Keyword coverage: red <70%, yellow <85%, green ≥85%."
            )
            with gr.Row():
                retrieval_k = gr.Slider(1, 10, value=5, step=1, label="k (top-k retrieved)")
                use_rewrite = gr.Checkbox(
                    value=True,
                    label="Rewrite follow-up questions first (matches production)",
                )
            retrieval_run = gr.Button("Run retrieval evaluation", variant="primary")
            retrieval_badges = gr.HTML()
            retrieval_table = gr.Dataframe(label="Per-case results", wrap=True)

            retrieval_run.click(
                run_retrieval_panel,
                inputs=[preset, model_override, api_key_override, retrieval_k, use_rewrite],
                outputs=[retrieval_badges, retrieval_table],
            )

        with gr.Tab("Generation quality (LLM judge)"):
            gr.Markdown(
                f"Judge model: `{_DEFAULT_SETTINGS.judge_llm_model or '(unset — see .env)'}` "
                "— fixed, so scores stay comparable across answering-model runs. "
                "0–5 per dimension: Accuracy (factually correct), Completeness (covers all "
                "aspects/reference info), Relevance (directly answers the question, no padding)."
            )
            with gr.Row():
                gen_k = gr.Slider(1, 10, value=5, step=1, label="k (top-k retrieved)")
                gen_baseline = gr.Checkbox(
                    value=False, label="Stuff-everything baseline (no retrieval)"
                )
            with gr.Row():
                gen_categories = gr.CheckboxGroup(_ALL_CATEGORIES, label="Categories (empty = all)")
                gen_limit = gr.Number(value=10, precision=0, label="Max cases (0 = all)")
            gr.Markdown(
                "⚠️ Each case is a full pipeline run + judge call — slow on local CPU models."
            )
            gen_run = gr.Button("Run generation evaluation", variant="primary")
            gen_status = gr.Markdown()
            gen_chart = gr.BarPlot(x="dimension", y="score", y_lim=[0, 5], label="Average score")
            gen_table = gr.Dataframe(label="Per-case results", wrap=True)

            gen_inputs = [
                preset,
                model_override,
                api_key_override,
                gen_k,
                gen_baseline,
                gen_categories,
                gen_limit,
            ]
            gen_run.click(
                run_generation_panel,
                inputs=gen_inputs,
                outputs=[gen_chart, gen_table, gen_status],
            )

    return app  # type: ignore[no-any-return]


if __name__ == "__main__":
    build_app().launch()
