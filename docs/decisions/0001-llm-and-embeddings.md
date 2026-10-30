# ADR-0001: LLM provider, model family, and embeddings

## Status
Accepted — 2026-10-29

## Context
The chat needs an LLM that follows instructions tightly (stay inside retrieved context, decline when the answer isn't there), handles Portuguese well, will eventually need reliable tool calling (v2+), and streams fast enough for a chat UI. Running a model well 24/7 requires either paying for GPU hosting or using a hosted inference provider.

## Options considered

**Small model, self-hosted via Ollama** (Gemma 4, small Qwen 3.x, Mistral Small, Phi-4)
- Pros: free, private, teaches serving/quantisation.
- Cons: 24/7 GPU hosting is expensive for a hobby project; weaker reasoning and tool calling.

**Mid/large open model via a hosted provider** (larger Qwen 3.x, gpt-oss-120b, Llama 4, Mistral)
- Pros: fast, smarter, better tool calling, free tiers available.
- Cons: data leaves to a third party; rate limits; models get deprecated/retired without notice.

## Decision
Use both, for different purposes:
- **Local development and offline tests:** small model in Ollama.
- **Production:** hosted provider serving a mid-size open model.

**Provider:** Groq first (free tier, very fast inference on open models), with OpenRouter or Together as fallback. All three expose OpenAI-compatible APIs, so switching providers is a config change, not a code change.

**Model family:** Qwen is the default shortlist for multilingual quality and tool use; Qwen 3/3.5 is Apache 2.0 licensed. Shortlist two or three candidate models and let the eval set (see `docs/design.md` § Evals) decide the final pick — do not hardcode a single model as "the" choice ahead of data.

**Embeddings:** a small multilingual model in the multilingual-e5 or bge-m3 class, run on CPU inside the backend process. Free, private, and fast enough for the expected ~50 chunks at this scale.

**Judge model for evals:** a different, stronger model than the one generating answers, to avoid a model grading its own work.

**Config, not code:** model name and base URL live in environment/config, never hardcoded, because provider catalogs change often (e.g. Groq retiring several Llama/Qwen models in June 2026 per public reports).

## Consequences
- Switching LLM provider or model is a config change plus an eval re-run, not a deploy of new code paths.
- Local dev behavior (Ollama) can diverge slightly from production (hosted model) — the eval set is what validates production behavior before each release, not local testing alone.
- A provider deprecating the chosen model is an explicit risk (see `docs/design.md` § Risks), mitigated by the fallback provider and by re-running evals before switching.

## Update — 2026-10-30: considered and reverted a lighter embeddings runtime

`sentence-transformers` + `intfloat/multilingual-e5-small` pulls in `torch` as a transitive dependency — a CPU-only build still costs ~540MB, and `backend/.venv` came to **1.8GB** total for a single small embedding model. That felt disproportionate for a 10-user hobby MVP, so we tried swapping to `fastembed` (ONNX Runtime, no torch) with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` instead — `.venv` dropped to 614MB.

That swap also meant a different, less-proven embedding model (fastembed's catalog doesn't carry `multilingual-e5-small`, only the 2.24GB `-large`), and re-verifying it against the sample group surfaced a real recall gap: a PT single-fact query for one member missed him in the top-3 because his name also appears in a cross-member story in two other members' docs — the lighter model was more easily diluted by that than e5-small was.

**Decided to revert and keep `sentence-transformers` + `intfloat/multilingual-e5-small`.** e5-class models are the more established, widely-benchmarked choice for RAG retrieval specifically (asymmetric query/passage training objective built for exactly this retrieval setup, not just general sentence similarity); the 1.8GB venv is an annoyance but a one-time local/CI cost, not a runtime or deployment cost that scales with usage. Retrieval quality is the thing this project is actually trying to learn and get right — not worth trading away for disk space at this stage. If the footprint becomes a real problem later (e.g. slow CI, constrained deploy image size), revisit with the eval suite in hand rather than switching blind again.
