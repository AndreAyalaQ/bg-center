# ADR-0005: Two-track evals with cheapest-first metrics

## Status
Accepted — 2026-10-29

## Context
Every change to prompt, chunking, top-k, or model needs a fast, repeatable way to tell whether the change made answers better or worse — both for engineering iteration (does this specific change help?) and for the private goal of actually working well for the real friend group. Running an LLM-as-judge on every PR against real personal data is both slow/costly and would leak real questions/answers into public CI logs.

## Options considered
- **One golden set, real data only, run in CI:** simplest, but leaks real personal data into public PR comments/logs, and is slow if it always runs the full LLM-judge pass.
- **Two tracks — fictional "sample" data in public CI, real data run locally/privately:** more setup (maintaining fictional data that mirrors the real data's shape), but keeps all real personal content out of the public repo's history while still giving fast, meaningful public CI signal.

## Decision
Two eval tracks sharing one runner:

| | Sample track | Real track |
|---|---|---|
| Data | `data/sample/` + `evals/sample_golden.yaml` | `bg-center-data` |
| Runs | Every PR in GitHub Actions, and locally | Locally before each release tag; later a private CI job |
| Answers | Did this change make it better or worse? | Is it good for our actual friends? |
| Committed publicly | Everything | Aggregate scores only, never questions or answers |

**Golden set:** 30–40 questions in `evals/golden.yaml` (and its sample equivalent), each with an expected answer, expected member(s), and a category: single-member fact, story, cross-member, follow-up, unanswerable, adversarial, Portuguese.

**Metrics, cheapest first** (cheaper checks run first; only promising changes pay for the expensive LLM-judge pass):
1. Retrieval recall@k — deterministic, no LLM call.
2. String checks on fact answers.
3. LLM-as-judge scoring correctness, faithfulness to retrieved context, and correct declines — using a judge model different from the answering model (ADR-0001).

**Variants compared from day one:** stuff-everything baseline vs RAG at k = 3, 5, 8, across two or three candidate models — so "is RAG even worth it on this data" is answered empirically, not assumed.

**Online feedback loop:** thumbs up/down in the UI is stored with the message and its trace; each thumbs-down is reviewed, and if it reflects a real failure, a fictional equivalent is added to the public sample golden set (never the real question/answer itself).

## Consequences
- Fictional member data must be deliberately engineered with "planted traps" (lookalike names, shared facts, clear extremes, cross-member stories, deliberately missing facts) so the sample track actually exercises the hard cases, not just easy ones.
- The public README's eval results table (baseline vs RAG vs agent, per version) is sourced from the sample track only, by design.
- A change that improves sample-track scores is not guaranteed to improve real-track scores until the real track is run locally before a release tag — the two tracks are correlated, not identical.
