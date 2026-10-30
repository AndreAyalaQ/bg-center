# backend

FastAPI app and RAG pipeline. Not yet implemented — see `docs/design.md` and the root `CLAUDE.md` build plan.

Planned layout (per `docs/design.md` § Architecture):
- Query rewrite (last 4 turns → standalone question)
- Retrieval (multilingual embeddings + in-memory Chroma)
- Grounded answer generation (streamed over SSE)
- `/api/auth`, `/api/members`, `/api/chat`, `/api/feedback` endpoints

Config (LLM provider/model, embeddings model, `DATA_DIR`, secrets) comes from environment variables — see `.env.example` at the repo root.
