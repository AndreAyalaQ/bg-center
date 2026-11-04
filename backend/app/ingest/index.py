"""In-memory vector index over member chunks, built at startup.

docs/design.md § Storage: "In-memory Chroma, built at startup" for the MVP —
the dataset is tiny and ephemeral disks don't matter because it's rebuilt
every time the process starts. Built on LangChain's Chroma vectorstore
(ADR-0006) rather than calling chromadb directly.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict

from app.ingest.chunker import Chunk, chunk_members
from app.ingest.embeddings import DEFAULT_MODEL, get_embeddings
from app.ingest.parser import load_members


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    member: str
    section: str
    source_file: str
    score: float  # cosine similarity, 1.0 = identical


class MemberIndex:
    """An in-memory LangChain Chroma vectorstore over one data directory's chunks."""

    def __init__(self, data_dir: Path, model_name: str = DEFAULT_MODEL) -> None:
        self.data_dir = data_dir
        self.model_name = model_name
        self._chunks_by_id: dict[str, Chunk] = {}
        # Each index gets its own collection name — chromadb's default
        # in-process client shares collection state process-wide, so two
        # MemberIndex instances in the same process (e.g. in tests) would
        # otherwise collide on "members".
        self._vectorstore = Chroma(
            collection_name=f"members-{uuid.uuid4().hex}",
            embedding_function=get_embeddings(model_name),
            collection_metadata={"hnsw:space": "cosine"},
        )
        self._build()

    def _build(self) -> None:
        members = load_members(self.data_dir)
        chunks = chunk_members(members)
        self._chunks_by_id = {chunk.id: chunk for chunk in chunks}
        if not chunks:
            return

        def metadata(chunk: Chunk) -> dict[str, str]:
            return {
                "member": chunk.member,
                "section": chunk.section,
                "source_file": chunk.source_file,
            }

        documents = [
            Document(page_content=chunk.text, metadata=metadata(chunk), id=chunk.id)
            for chunk in chunks
        ]
        self._vectorstore.add_documents(documents, ids=[c.id for c in chunks])

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
        k = min(k, len(self._chunks_by_id))
        results = self._vectorstore.similarity_search_with_score(text, k=k)
        retrieved = []
        for document, distance in results:
            assert document.id is not None
            chunk = self._chunks_by_id[document.id]
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
