"""Embedding model wrapper — a small multilingual model, run on CPU (ADR-0001).

Built on LangChain (ADR-0006): `HuggingFaceEmbeddings` wraps the same
`intfloat/multilingual-e5-small` sentence-transformers model as before.
e5 models expect a "query: "/"passage: " prefix on the input text — that's
part of how the model was trained, not something LangChain's generic
wrapper knows about, so `E5Embeddings` adds it.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

DEFAULT_MODEL = "intfloat/multilingual-e5-small"


class E5Embeddings(Embeddings):
    """Adds e5's "query: "/"passage: " prefix convention around a HuggingFace embedder."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents([f"passage: {text}" for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(f"query: {text}")


@lru_cache
def get_embeddings(model_name: str = DEFAULT_MODEL) -> E5Embeddings:
    return E5Embeddings(model_name)
