"""Embedding model wrapper — a small multilingual model, run on CPU (ADR-0001).

Runs via fastembed (ONNX Runtime) rather than sentence-transformers/torch:
same "small multilingual model on CPU" requirement, without pulling in a
~1.8GB torch install for a single model. See docs/decisions/0001 for the
full tradeoff.

sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 covers 50+
languages including Portuguese and is a symmetric model — queries and
passages are embedded the same way, unlike e5's "query: "/"passage: "
prefix convention.
"""

from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache
def _model(name: str) -> TextEmbedding:
    return TextEmbedding(model_name=name)


def embed_passages(texts: list[str], model_name: str = DEFAULT_MODEL) -> list[list[float]]:
    model = _model(model_name)
    return [vec.tolist() for vec in model.embed(texts)]


def embed_query(text: str, model_name: str = DEFAULT_MODEL) -> list[float]:
    model = _model(model_name)
    vector = next(iter(model.query_embed([text])))
    result: list[float] = vector.tolist()
    return result
