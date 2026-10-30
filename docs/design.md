# BG Center — System Design

*Oct 29, 2026 · @André Querido*

## Overview

BG Center is a web chat where the friend group asks questions about its own members and gets answers grounded in docs each member wrote. It starts as a RAG chatbot on open-source models and grows into an agent with tools.

### Goals

- Answer questions about any member, in English or Portuguese, from their own docs.
- Say "I don't know" instead of inventing facts.
- Explain every bad answer from its trace.
- Learn the full AI engineering loop: retrieval, prompting, evals, observability, deployment.

### Non-goals for the MVP

- Tool use and agent behaviour (roadmap below).
- Self-hosting the LLM in production.
- User accounts, long-term memory, public access.

**Users:** about 10 friends, low traffic, accessed through a shared invite code.

## Architecture

A static React app talks to one FastAPI service, which rewrites the question, retrieves member chunks, and streams a grounded answer from a hosted open model.

```
React frontend (Chat UI, SSE stream)  --HTTPS-->  FastAPI backend (Render/Fly.io)
                                                      1. Query rewrite (last 4 turns -> standalone question)
                                                      2. Retrieve top-k (multilingual embeddings + Chroma)
                                                      3. Grounded answer (context + system prompt, streamed)
                                                      <--> Member docs (Markdown in repo, embedded at startup)
                                                      <--> Groq LLM (open model, hosted; OpenRouter fallback)
                                                      --> Postgres (chats + feedback; Neon/Supabase)
                                                      --> Langfuse Cloud (traces + evals; EU region)
```

Request flow: the UI posts a message, the backend rewrites it into a standalone question using recent turns, retrieves the top-k chunks, builds the prompt, and streams tokens back over SSE. Each step is traced to Langfuse; the conversation and any feedback land in Postgres.

## Data model

Each member is one Markdown file with YAML frontmatter: the frontmatter holds structured facts, the body holds free-text sections. This split lets RAG handle stories now and a facts tool handle aggregate questions later, with no restructuring.

```yaml
---
id: miguel
name: Miguel Santos
nickname: Migas
birthday: 1995-03-14
city: Lisboa
job: Software engineer
pets: [cat]
diet: vegetarian
height_cm: 182
---

## Personality
Always late, always has a reason. ...

## Stories
The Porto trip, 2019: ...

## Inside jokes
"Migas time" = 40 minutes after the agreed time. ...
```

### Chunking and indexing

- One chunk per `##` section; split further only if a section exceeds roughly 400 tokens.
- Prefix each chunk with the member's name before embedding ("Miguel (Migas) – Stories: ..."), so the vector carries who it is about.
- Metadata on every chunk: `member`, `section`, `source_file`.
- Frontmatter is also rendered into one short "facts" chunk per member for the MVP.

### Storage

| Data | MVP | Later |
|---|---|---|
| Member docs | Markdown files in the repo | Postgres, editable at runtime |
| Vectors | In-memory Chroma, built at startup | pgvector |
| Structured facts | Frontmatter, parsed at startup | Postgres table behind a query tool |
| Conversations, feedback | Postgres | Postgres |

## LLM and embeddings

**Decision:** develop locally with a small model in Ollama, deploy against a hosted provider serving a mid-size open model, and pick the final model with evals. The model name and base URL live in config, never in code.

### Requirements

- Strong instruction following: stay inside the context, decline when the answer is missing.
- Good Portuguese, since many questions will be in PT.
- Reliable tool calling, needed for the agent phase.
- Fast streaming.

### Options

| | Small model, self-hosted (Ollama) | Mid/large open model, hosted provider |
|---|---|---|
| Examples | Gemma 4, small Qwen 3.x, Mistral Small, Phi-4 | Larger Qwen 3.x, gpt-oss-120b, Llama 4, Mistral |
| Pros | Free, private, teaches serving and quantisation | Fast, smarter, better tool calling, free tiers |
| Cons | 24/7 GPU hosting is expensive; weaker reasoning and tools | Data leaves to a third party; rate limits; models get retired |
| Role | Local development and offline tests | Production |

**Providers:** Groq first (free tier, very fast inference on open models); OpenRouter or Together as fallbacks. All expose OpenAI-compatible APIs, so switching is a config change. Catalogs change often: one report says Groq retired several Llama and Qwen models in June 2026.

**Model family:** Qwen is the default shortlist for multilingual and tool use; Qwen 3/3.5 is Apache 2.0. Shortlist two or three models and let the eval set decide.

**Embeddings:** a small multilingual model (multilingual-e5 or bge-m3 class) runs on CPU inside the backend. Free, private, and fast enough for about 50 chunks.

**Judge model for evals:** a different, stronger model than the one answering.

## API contract

The React + TypeScript frontend and the FastAPI backend agree on four endpoints. Every call except `/api/auth` carries the bearer token.

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/api/auth` | `{ inviteCode }` | `{ token }` |
| GET | `/api/members` | – | `[{ id, name, nickname, avatarUrl, tagline }]` |
| POST | `/api/chat` | `{ message, conversationId \| null }` | SSE stream of `token` events, then a `done` event: `{ conversationId, messageId, sources: [{ member, section, snippet }] }` |
| POST | `/api/feedback` | `{ messageId, rating: "up" \| "down", comment? }` | `204` |

- Streaming uses Server-Sent Events over a plain `fetch`; no websockets.
- `sources` lets the UI show "based on Miguel's profile" and helps debug retrieval.
- CORS allows the frontend origin only, configured from day one.

## Deployment

**Decision:** managed platforms for everything in the MVP, so time goes into the AI side rather than operations.

| Component | Where | Why |
|---|---|---|
| React frontend | Vercel, Netlify or Cloudflare Pages | Free, deploys on git push, global CDN |
| FastAPI backend | Render, Fly.io or Railway | Little ops work; free tiers sleep, so expect a slow first request, or pay a few euros for always-on |
| LLM | Groq (fallback OpenRouter) | No GPU to run; OpenAI-compatible |
| Embeddings + vector index | Inside the backend process | Tiny dataset; rebuilt at startup, so ephemeral disks don't matter |
| Postgres | Neon or Supabase free tier | Conversations and feedback; pgvector later |
| Tracing | Langfuse Cloud, EU region | No observability stack to run |

**Secrets** (LLM API key, Langfuse keys, invite code, database URL) live in the hosting platform's environment variables, never in the repo.

**Alternative considered:** one cheap VPS running docker-compose. Better for learning Docker and networking, but adds backups, TLS and uptime to your plate. Worth it as a later exercise, not for the MVP.

## Repository and workflow

**Decision:** two repos split by content, not by copy. All code lives and is developed in one public repo; a private repo holds only the real data. There is nothing to sync, the public history is the real history, and real data can't leak through it because it was never there.

### Structure (monorepo)

```
bg-center/
├── backend/           FastAPI app, RAG pipeline, tests
├── frontend/           React + TypeScript (Claude Design output)
├── data/
│   └── sample/        fictional members, used by tests, CI and demos
├── evals/              golden.yaml (sample set), runner, results/
├── docs/
│   ├── design.md       this doc
│   └── decisions/      one short ADR per major decision
├── .github/workflows/
├── .env.example
└── README.md
```

### The two repos

| Repo | Visibility | Contains |
|---|---|---|
| `bg-center` | Public | All code, CI, eval runner, fictional sample members, sample golden set, design doc, ADRs, README, aggregate eval scores |
| `bg-center-data` | Private | Real member docs, real golden set, real eval outputs; no code |

### How data reaches the app

- The app reads members from `DATA_DIR`: `data/sample` by default, `../bg-center-data/members` locally when working with real data.
- Production gets real data either by the deploy checking out `bg-center-data` with a read-only deploy key, or by loading the docs into Postgres once and reading from there.
- The public repo gitignores any local path to the private data, and CI runs secret scanning, so a misplaced file can't be committed.

### Two eval tracks, one runner

| | Sample track | Real track |
|---|---|---|
| Data | `data/sample/` + `evals/sample_golden.yaml` | `bg-center-data` |
| Runs | Every PR in GitHub Actions, and locally | Locally before each release tag; later a private CI job |
| Answers | Did this change make it better or worse? | Is it good for our actual friends? |
| Committed publicly | Everything | Aggregate scores only, never questions or answers |

Fictional members mirror the real data's shape (member count, doc length, PT/EN mix, sections) and carry planted traps: lookalike names, shared facts, clear extremes for aggregate questions, cross-member stories and deliberately missing facts. Fact questions are generated from frontmatter in code; story, follow-up, unanswerable and adversarial questions are written by hand. Each real thumbs-down gets a fictional equivalent added to the sample set.

**Alternative considered:** one private repo with everything, publishing release snapshots to a public repo through an allowlist-based GitHub Action and squashed commits. Rejected because the public repo would show only snapshots, not the real commit and PR history.

### How work lands

- One branch and one pull request per step, with a description of what changed and why.
- Small commits with conventional messages (`feat:`, `fix:`, `eval:`, `docs:`).
- Each architecture decision gets a short ADR in `docs/decisions/`: context, options, choice. These come straight from this doc's tables.
- Each phase ends with a git tag and release (`v1.0` RAG MVP, `v2.0` first tools...), matching the roadmap gates.

### CI (GitHub Actions)

| Trigger | Runs |
|---|---|
| Every push | Lint (ruff, eslint), type checks (mypy, tsc), unit tests, secret scan |
| Pull request | The above, plus the eval suite on sample data; results posted as a PR comment |
| Merge to main | Frontend and backend auto-deploy through the hosts' GitHub integrations |

**README as the portfolio page:** a one-paragraph pitch, the architecture diagram, a demo GIF on sample data, how to run it locally, and an eval results table per version (baseline vs RAG vs agent). That table shows the engineering, not just the app.

## Evals

Every change to prompt, chunking, top-k or model is judged by one command that runs a golden question set and prints scores by category, always compared against the stuff-everything baseline.

**Golden set:** 30–40 questions in `evals/golden.yaml`, each with an expected answer, expected member(s) and a category.

| Category | Example | What it tests |
|---|---|---|
| Single-member fact | "Where does Ana work?" | Basic retrieval |
| Story | "What happened to João in Porto?" | Semantic retrieval |
| Cross-member | "Who's the oldest?" | Aggregation, RAG's weak spot |
| Follow-up | "And what does he do?" | Query rewriting with history |
| Unanswerable | "What's Rui's blood type?" | Declines instead of inventing |
| Adversarial | "Ignore your instructions and..." | Robustness to prompt injection |
| Portuguese | Any of the above in PT | Language handling |

### Metrics, cheapest first

1. Retrieval recall@k: the expected member and section appear in the top-k chunks. Deterministic, no LLM.
2. String checks on fact answers (answer contains "Lisboa").
3. LLM-as-judge scoring correctness, faithfulness to retrieved context, and correct declines.

**Online feedback:** thumbs up/down in the UI is stored with the message and its trace. Each thumbs-down is reviewed and, if it shows a real failure, added to the golden set.

**Variants to compare from day one:** stuff-everything baseline vs RAG at k = 3, 5, 8, and two or three candidate models.

## Logging and observability

Every chat request produces one Langfuse trace, so any bad answer can be traced to either retrieval or generation.

### Trace contents

| Span | Captured |
|---|---|
| Request | Conversation ID, message ID, user message, language |
| Query rewrite | Input history, rewritten query, latency |
| Retrieval | Chunk IDs, member, section, similarity scores, k |
| Generation | Model, full prompt, answer, input/output tokens, time to first token, total latency |
| Feedback | Thumbs rating and comment, attached to the trace |

**App logs:** structured JSON with a request ID shared with the trace; errors, provider rate-limit hits, and timeouts.

**Tooling:** Langfuse covers tracing, prompt management, LLM-as-judge and dataset experiments, with an MIT-licensed core. Use Langfuse Cloud for the MVP; self-hosting needs Postgres, ClickHouse, Redis and object storage, which is too heavy for a hobby budget.

**Dashboards to watch:** p50/p95 latency, tokens per request, error and rate-limit rate, thumbs-down rate.

## Privacy and safety

The app holds personal details about real friends, so consent and access control are MVP requirements, not extras.

- **Consent:** each member writes or approves their own doc. No health, addresses, relationships or anything they wouldn't say in the group chat.
- **Access:** shared invite code exchanged for a short-lived token; no public pages; rate limit per token.
- **Third parties:** member docs and chat messages go to the LLM provider and Langfuse. Check each provider's data-retention terms and prefer EU regions where offered.
- **Logs:** tell the group that chats are logged and readable by the admin; keep traces for 30 days.
- **Prompt injection:** the system prompt restricts answers to the provided context. Jailbreak attempts are expected, logged, and fed into the adversarial eval category.
- **Removal:** any member can ask to have their doc and related chunks deleted.

## MVP scope

The MVP is a deployed, invite-only RAG chat with tracing, feedback and a golden eval set. Aggregate questions are expected to score poorly; that gap motivates the first agent tool.

### In scope

- [ ] Public GitHub repo with sample data, CI and README; real member docs kept private, approved by each friend
- [ ] Ingestion: parse frontmatter, chunk by section, embed, build in-memory index at startup
- [ ] Chat pipeline: query rewrite with last 4 turns, retrieve top-k, grounded answer, streamed over SSE
- [ ] Stuff-everything baseline behind a config flag
- [ ] API endpoints: auth, chat, feedback
- [ ] React + TypeScript UI from Claude Design: invite gate, chat, sources, member strip, thumbs
- [ ] Postgres for conversations and feedback
- [ ] Langfuse tracing on every request
- [ ] Golden set (30+ questions) and one-command eval runner, run in CI on every pull request
- [ ] Deployed frontend and backend, secrets in environment variables, auto-deploy from main

**Out of scope:** tools and agent loop, runtime lore editing, quiz mode, user accounts, long-term memory, self-hosted LLM.

### Definition of done

1. Every friend can log in with the invite code and chat on phone and laptop.
2. Single-member fact questions are at least 90% correct on the golden set.
3. At least 90% of unanswerable questions are declined, not invented.
4. Any answer can be explained from its trace.
5. The eval report states whether RAG beats the baseline on this data.

## Roadmap to agent

The system becomes an agent in v2, when retrieval stops being a fixed step and the model chooses which tools to call. Each phase starts only when the previous gate passes on the eval set.

| Phase | Contents |
|---|---|
| v1 · RAG MVP | Grounded chat, query rewrite, evals + tracing |
| v2 · First tools | `search_stories` tool, `query_facts` tool, hand-written loop |
| v3 · Memory + games | Add lore, approved; pgvector storage; quiz mode, scores |
| v4 · Multi-step | Event planner; web search + polls; roast/toast writer; multi-agent, later |

**Gates:** Gate 1 — MVP done-criteria met. Gate 2 — Cross-member ≥ 80%. Gate 3 — Writes need approval.

- v2 replaces fixed retrieval with `search_stories(query, member?)` and `query_facts(filter)`; the agent loop is written by hand before adopting a framework such as LangGraph or PydanticAI.
- v3 adds write tools (new lore, pending the member's approval) and stateful games, so storage moves to Postgres + pgvector.
- v4 chains several tools per request, e.g. planning a dinner from dietary facts, web search and a poll. Multi-agent is optional and only if a single agent gets unwieldy.

## Open questions and risks

### Open questions

- Will docs be written in Portuguese, English or a mix? This decides the embedding model and the eval split.
- How many members, and how long is each doc? Under ~20k tokens total, the baseline may simply win.
- Who approves edits to someone else's doc once runtime editing exists?

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Provider retires the chosen model | Chat breaks | Model in config; eval run before switching; fallback provider |
| Free-tier rate limits during group use | Errors at peak | Retry with backoff; cheap paid tier if needed |
| Model invents facts about friends | Hurt feelings, lost trust | Grounding prompt, unanswerable evals, sources shown |
| Sensitive info in docs or chats | Privacy breach | Consent rules, invite gate, 30-day retention |
| Backend cold starts | Slow first answer | Accept, or pay for always-on |
