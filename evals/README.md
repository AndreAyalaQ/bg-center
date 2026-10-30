# evals

Golden-set eval runner — see ADR-0005 and `docs/design.md` § Evals.

Planned contents:
- `golden.yaml` — real golden set (lives in `bg-center-data`, not here)
- `sample_golden.yaml` — fictional-data equivalent, committed publicly, run on every PR
- a runner script that scores retrieval recall@k, string checks, and LLM-as-judge correctness/faithfulness/decline-handling, compared against the stuff-everything baseline
- `results/` — eval run outputs

Not yet implemented.
