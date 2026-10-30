"""Embedding model wrapper — a small multilingual model, run on CPU (ADR-0001).

intfloat/multilingual-e5-small is the small end of ADR-0001's shortlist:
free, private, and fast enough for the dataset size expected at this scale
(docs/design.md § LLM and embeddings). e5 models expect a "query: " /
"passage: " prefix on the input text — that's part of how the model was
trained, not a project convention.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "intfloat/multilingual-e5-small"


@lru_cache
def _model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name, device="cpu")


def embed_passages(texts: list[str], model_name: str = DEFAULT_MODEL) -> list[list[float]]:
    model = _model(model_name)
    prefixed = [f"passage: {text}" for text in texts]
    return model.encode(prefixed, normalize_embeddings=True).tolist()  # type: ignore[no-any-return]


def embed_query(text: str, model_name: str = DEFAULT_MODEL) -> list[float]:
    model = _model(model_name)
    return model.encode(f"query: {text}", normalize_embeddings=True).tolist()  # type: ignore[no-any-return]
