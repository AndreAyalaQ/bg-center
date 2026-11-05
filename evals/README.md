# Evals

A fixed set of questions with known answers, used to measure the chatbot every time the prompt, chunking, retrieval settings or model changes. Scores are reported per category, so a drop points straight at the part of the pipeline that broke.

## Files

| File | What it is | Edit it? |
| --- | --- | --- |
| `sample_golden.yaml` | Hand-written cases: stories, follow-ups, lookalikes, unanswerable, adversarial, injection | Yes |
| `generate_fact_questions.py` | Reads member frontmatter, writes fact and aggregate cases with computed answers, validates all cases | Yes |
| `sample_golden.generated.yaml` | Output of the generator | No, regenerate it |
| `cases.py` | Pydantic `GoldenCase` schema + loader, merges both golden files | Yes |
| `metrics.py` | Retrieval metrics: Mean Reciprocal Rank, nDCG, keyword coverage | Yes |
| `retrieval_eval.py` | Runs `metrics.py` across the golden set against a `MemberIndex` | Yes |
| `judge.py` | LLM-as-judge: scores a generated answer 0–5 on Accuracy/Completeness/Relevance | Yes |
| `generation_eval.py` | Runs the full chat pipeline per case, then `judge.py` | Yes |
| `eval_ui.py` | Gradio dashboard over the above — see § Usage | Yes |

All cases here use the fictional group in `data/sample/`. Real-data cases live in the private `bg-center-data` repo and use the same format.

No `evals/run.py` CLI exists yet — the runner logic lives in the modules above (and `evals/eval_ui.py` for interactive use). A thin CLI wrapper calling the same functions is a reasonable addition if a non-interactive/CI path is needed later.

## Categories

| Category | Tests | Example | A low score points to |
| --- | --- | --- | --- |
| `single_fact` | One fact about one person | "Where does Pipo live?" | Retrieval basics: chunking, embeddings, top-k |
| `story` | Finding content by meaning | "What happened when Rita and Tomás went to Porto?" | Embedding quality, chunk boundaries |
| `cross_member` | Combining facts across members | "Who is the tallest?" | A limit of plain RAG; fixed by the v2 tools |
| `lookalike` | Similar names or nicknames | "What's the name of Joana's dog?" | Retrieval mixing up people |
| `stale_fact` | Current vs past facts | "Where does Diogo live now?" | Prompt not favouring current facts |
| `follow_up` | Questions that depend on earlier turns | "And what does she do for work?" | The query-rewrite step |
| `unanswerable` | No answer exists in the data | "What's Tomás's blood type?" | Hallucination: system prompt or model |
| `adversarial` | User tries to break the rules | "Ignore your instructions and…" | System prompt robustness |
| `injection` | Instructions hidden inside a document | Last section of `joana.md` | Context not treated as data |

## Case format

Every field is shown below for reference; a real case uses only the ones it needs.

```yaml
- id: lookalike-joana-dog            # unique and stable; results are compared by id
  category: lookalike                 # one of the categories above
  language: en                        # en | pt
  history:                            # optional: earlier user turns, oldest first
    - "Who in the group has a dog?"
  question: "What's the name of Joana's dog?"
  expected_members: [joana]           # docs retrieval should return
  expected_section: stories           # optional
  must_contain: [Hipotenusa]          # every string must appear
  must_contain_any: [Lisboa, Lisbon]  # at least one must appear
  must_not_contain: [Bolacha]         # none may appear
  expect_decline: true                # the answer must say it doesn't know
  judge_rubric: "Says Joana has no pets."   # what the LLM judge checks
```

Every case needs at least one of `must_contain`, `must_contain_any`, `expect_decline` or `judge_rubric`. The generator refuses to run otherwise.

## How cases are graded

Two independent tracks, cheapest first:

**Retrieval quality** (`metrics.py`, `retrieval_eval.py`) — no LLM generation needed, just embeddings + vector search:
- **Mean Reciprocal Rank.** 1/rank of the first retrieved chunk whose `member` is in `expected_members`; 0 if none found.
- **nDCG.** Binary relevance (member match), normalized against the ideal ordering of the *same retrieved set* — there's no corpus-wide relevance judgment, only per-case `expected_members`.
- **Keyword coverage.** Fraction of `must_contain`/`must_contain_any` found in the *retrieved chunk text* (not the generated answer) — case- and accent-insensitive, so "Ines" matches "Inês".
- Cases with `expected_members: []` (most `adversarial`/`injection` cases — there's no "correct person" to retrieve for "list everyone's address") are excluded from the MRR/nDCG average, not scored as 0.
- A `follow_up` case's `question` is a raw fragment ("And what does he do?"); when a `Settings` is passed, it's rewritten to a standalone question with the *same model being evaluated* first, matching what production actually does — skipping this would make follow-up retrieval look artificially weak for a reason that has nothing to do with retrieval.

**Generation quality** (`judge.py`, `generation_eval.py`) — runs the full pipeline, then an LLM judge (a different, stronger model than the one answering, via `JUDGE_LLM_MODEL`) scores the answer 0–5 on:
- **Accuracy** — factually correct per the retrieved context (or, for `expect_decline` cases, correctly declines instead of inventing).
- **Completeness** — covers all aspects of the question and all relevant info in the context/`judge_rubric`.
- **Relevance** — directly answers the question asked, no padding or unrelated information.

Compare against the stuff-everything baseline (all member docs in the prompt, no retrieval) by toggling the baseline flag/checkbox and re-running — not yet automatic in one run.

## Usage

Generate fact questions and validate all cases (run after editing any member doc):

```bash
python evals/generate_fact_questions.py
```

Same thing on the private data:

```bash
python evals/generate_fact_questions.py \
  --data ../bg-center-data/members \
  --out ../bg-center-data/golden.generated.yaml \
  --hand-written ../bg-center-data/golden.yaml
```

Interactive dashboard (retrieval metrics + LLM-judge generation scoring), from the repo root:

```bash
backend/.venv/bin/python -m evals.eval_ui
# -> http://127.0.0.1:7860
```

Needs the `ui` extra: `cd backend && .venv/bin/pip install -e ".[ui]"`. The generation panel runs a full pipeline + judge call per case — slow against a local CPU model; use the category filter and "Max cases" to iterate quickly, and prefer a hosted provider (Groq) for a full run.

Or call the runner functions directly, e.g. in a notebook or script (from the repo root, using `backend/.venv/bin/python`):

```python
from pathlib import Path
from app.ingest.index import MemberIndex
from evals.retrieval_eval import run_retrieval_eval

index = MemberIndex(Path("data/sample/members"))
report = run_retrieval_eval(index, k=5)
print(report.mean_reciprocal_rank, report.mean_ndcg, report.mean_keyword_coverage)
```

## Adding a case

- **A fact from frontmatter?** Don't write it by hand. Add or change the field in the member doc and regenerate.
- **Anything else:** add it to `sample_golden.yaml` under its category, with a new unique `id`.
- **A real failure** (a friend's thumbs-down): write a fictional equivalent here so the public suite learns from it, and the real version in the private repo.
- Never change an existing `id`; results are tracked by it across runs.

## Public vs private

| | Sample track (this folder) | Real track (`bg-center-data`) |
| --- | --- | --- |
| Data | Fictional members | Real friends |
| Runs | Every pull request in CI, and locally | Locally before each release tag |
| Tells you | Whether a change made things better or worse | Whether the bot is good for the real group |
| Committed to the public repo | Everything | Aggregate scores only |