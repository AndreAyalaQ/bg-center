"""In-memory vector index over member chunks, built at startup.

docs/design.md § Storage: "In-memory Chroma, built at startup" for the MVP —
the dataset is tiny and ephemeral disks don't matter because it's rebuilt
every time the process starts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import chromadb

from app.ingest.chunker import Chunk, chunk_members
from app.ingest.embeddings import DEFAULT_MODEL, embed_passages, embed_query
from app.ingest.parser import load_members


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    member: str
    section: str
    source_file: str
    score: float  # cosine similarity, 1.0 = identical


class MemberIndex:
    """An in-memory Chroma collection over one data directory's chunks."""

    def __init__(self, data_dir: Path, model_name: str = DEFAULT_MODEL) -> None:
        self.data_dir = data_dir
        self.model_name = model_name
        self._chunks_by_id: dict[str, Chunk] = {}
        # chromadb.Client() shares collection state process-wide, so each
        # index needs its own collection name to avoid colliding with any
        # other MemberIndex built in the same process (e.g. in tests).
        self._collection = chromadb.Client().create_collection(
            name=f"members-{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"}
        )
        self._build()

    def _build(self) -> None:
        members = load_members(self.data_dir)
        chunks = chunk_members(members)
        self._chunks_by_id = {chunk.id: chunk for chunk in chunks}
        if not chunks:
            return
        embeddings = embed_passages([c.text for c in chunks], self.model_name)

        def metadata(chunk: Chunk) -> dict[str, str]:
            return {
                "member": chunk.member,
                "section": chunk.section,
                "source_file": chunk.source_file,
            }

        self._collection.add(
            ids=[c.id for c in chunks],
            embeddings=embeddings,  # type: ignore[arg-type]
            documents=[c.text for c in chunks],
            metadatas=[metadata(c) for c in chunks],
        )

    @property
    def size(self) -> int:
        return len(self._chunks_by_id)

    def all_chunks(self) -> list[RetrievedChunk]:
        """Every chunk, unranked — for the stuff-everything baseline (ADR-0005)."""
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                text=chunk.text,
                member=chunk.member,
                section=chunk.section,
                source_file=chunk.source_file,
                score=1.0,
            )
            for chunk in self._chunks_by_id.values()
        ]

    def query(self, text: str, k: int = 5) -> list[RetrievedChunk]:
        if not self._chunks_by_id:
            return []
        query_embedding = embed_query(text, self.model_name)
        result = self._collection.query(
            query_embeddings=[query_embedding],  # type: ignore[arg-type]
            n_results=min(k, len(self._chunks_by_id)),
        )
        ids = result["ids"][0]
        distances = (result["distances"] or [[]])[0]
        retrieved = []
        for chunk_id, distance in zip(ids, distances, strict=True):
            chunk = self._chunks_by_id[chunk_id]
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    member=chunk.member,
                    section=chunk.section,
                    source_file=chunk.source_file,
                    score=1 - distance,
                )
            )
        return retrieved
