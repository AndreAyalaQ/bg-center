# ADR-0006: Adopt LangChain for embeddings/vector store, pydantic for data classes

## Status
Accepted — 2026-11-01

## Context
ADR-0001 and the ingestion/chat pipeline (steps 3–4) were built hand-rolled: `sentence-transformers` called directly for embeddings, `chromadb` called directly as the vector store, plain `@dataclass(frozen=True)` for internal data shapes (`Member`, `Section`, `Chunk`, `RetrievedChunk`, `ChatTurn`, `ChatResult`). That was a deliberate choice at the time — see `docs/decisions/0001-llm-and-embeddings.md` and the project's stated philosophy in `docs/design.md` § Roadmap ("the agent loop is written by hand before adopting a framework").

Reconsidered: LangChain is the de facto industry-standard framework for RAG pipelines, and learning it is a legitimate goal in its own right for a portfolio/learning project — distinct from, and in this case outweighing, the "avoid unnecessary framework weight" argument that drove the original hand-rolled choice.

## Decision

**Use LangChain for embeddings and the vector store; keep custom chunking.**

- `langchain-huggingface`'s `HuggingFaceEmbeddings` wraps the same `intfloat/multilingual-e5-small` sentence-transformers model as before — wrapped in a small custom `E5Embeddings` subclass of `langchain_core.embeddings.Embeddings` that adds the "query: "/"passage: " prefix e5 models require, since LangChain's wrapper doesn't know about that convention.
- `langchain-chroma`'s `Chroma` vectorstore replaces direct `chromadb` client calls in `app/ingest/index.py`.
- Parsing (`app/ingest/parser.py`) and chunking (`app/ingest/chunker.py`) stay custom — LangChain's generic document loaders/text splitters don't fit ADR-0004's bespoke section-based chunking, PT/EN heading normalization, or synthesized facts chunk, and reshaping that logic to fit LangChain's abstractions would cost more than it returns.
- Only the modern, scoped integration packages are used (`langchain-core`, `langchain-huggingface`, `langchain-chroma`), not the monolithic `langchain` + `langchain-community` combo — keeps the dependency footprint closer to what we actually use.

**Use pydantic `BaseModel` for data classes going forward**, not `@dataclass`. Applies to `Member`, `Section` (parser), `Chunk` (chunker), `RetrievedChunk` (index), `ChatTurn` (chat). Frozen via `model_config = ConfigDict(frozen=True)`, matching the immutability the dataclasses had. `ChatResult` (pipeline) is the one exception — it carries a live `Iterator[str]` of streaming tokens, which doesn't fit pydantic's validate/serialize model; it stays a plain dataclass with a documented reason, rather than forced into pydantic for the sake of a blanket rule. `app/config.py`'s `Settings` was already pydantic (via `pydantic-settings`), so no change there.

## Consequences
- The agent loop (v2+) explicitly still starts hand-written per `docs/design.md` § Roadmap — this ADR does not reopen that call. LangChain's role here is retrieval infrastructure (embeddings + vector store), not an agent framework.
- Chunking logic is unaffected: `Chunk`/`Section`/`Member` keep the same fields and construction sites, just as pydantic models instead of dataclasses — consuming code (tests, `chunker.py`, `index.py`) needed no logic changes, only the class definitions.
- `index.py`'s public interface (`MemberIndex.query`, `.all_chunks`, `.size`) is preserved, so `app/chat/pipeline.py` and its tests don't need to change.
- Dependency footprint grows modestly (`langchain-core`, `langchain-huggingface`, `langchain-chroma` are pure-Python, no new heavy transitive deps beyond what `sentence-transformers`/`chromadb` already pulled in).
- Future ingestion/retrieval work should default to LangChain's primitives (`Document`, `Embeddings`, vectorstore interfaces) where they fit, rather than reaching back to raw `chromadb`/`sentence-transformers` calls, so the codebase doesn't end up with two parallel approaches.
