# BG Center

A web chat where a friend group asks questions about its own members and gets answers grounded in docs each member wrote. Starts as a RAG chatbot on open-source models (v1), grows into an agent with tools (v2+).

Full system design: [`docs/design.md`](docs/design.md). Architecture decisions and their rationale: [`docs/decisions/`](docs/decisions/). Build plan for contributors (including Claude Code sessions): [`CLAUDE.md`](CLAUDE.md).

## Status

🚧 Pre-implementation. Repository structure and design docs are in place; backend, frontend, and eval runner are not yet built. See `CLAUDE.md` for the step-by-step plan and `docs/design.md` § MVP scope for the done-criteria checklist.

## Architecture

```
React frontend (Chat UI, SSE stream)  --HTTPS-->  FastAPI backend
                                                      1. Query rewrite
                                                      2. Retrieve top-k (embeddings + Chroma)
                                                      3. Grounded answer (streamed)
                                                      <--> Member docs
                                                      <--> Hosted LLM (Groq, OpenAI-compatible)
                                                      --> Postgres (chats + feedback)
                                                      --> Langfuse (traces + evals)
```

See `docs/design.md` § Architecture for the full request flow.

## Repository layout

```
bg-center/
├── backend/           FastAPI app, RAG pipeline, tests
├── frontend/           React + TypeScript
├── data/sample/         fictional members — used by tests, CI, demos
├── evals/               golden set + eval runner
├── docs/
│   ├── design.md        full system design
│   └── decisions/        one ADR per major decision
└── .github/workflows/    CI
```

Real member docs live in a separate **private** repo, `bg-center-data` — never in this repo. See `docs/decisions/0003-two-repo-split.md` for why.

## Local development

Not yet runnable — see `CLAUDE.md` for the build plan. Once implemented:

```bash
cp .env.example .env   # fill in LLM provider key, etc.
# backend and frontend run instructions will go here once they exist
```

## Evals

Every change to prompt, chunking, top-k, or model is judged against a golden question set, compared against a stuff-everything baseline. See `docs/decisions/0005-eval-strategy.md`.

| Version | Baseline | RAG | Agent |
|---|---|---|---|
| v1 | — | — | — |

*(Table fills in once the eval runner exists.)*
