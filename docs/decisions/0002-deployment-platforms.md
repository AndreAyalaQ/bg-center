# ADR-0002: Deployment on managed platforms

## Status
Accepted — 2026-10-29

## Context
The MVP needs to be reachable by ~10 friends over the internet, with Postgres for chats/feedback and tracing for debugging. The two realistic paths are managed PaaS/SaaS for every component, or self-managing one VPS with docker-compose.

## Options considered

**Managed platforms per component**
- React frontend on Vercel/Netlify/Cloudflare Pages, FastAPI backend on Render/Fly.io/Railway, Postgres on Neon/Supabase, tracing on Langfuse Cloud.
- Pros: near-zero ops work, free tiers cover this traffic level, deploy-on-push.
- Cons: backend free tiers sleep (slow first request unless paid for always-on); vendor-specific config.

**Single VPS with docker-compose**
- Pros: good learning exercise for Docker/networking; full control.
- Cons: owner is now responsible for backups, TLS, and uptime — meaningful extra surface for a hobby project with 10 users.

## Decision
Use managed platforms for every component in the MVP, so engineering time goes into the AI/retrieval side rather than infrastructure operations:

| Component | Where |
|---|---|
| React frontend | Vercel, Netlify, or Cloudflare Pages |
| FastAPI backend | Render, Fly.io, or Railway |
| LLM | Groq (OpenRouter fallback) |
| Embeddings + vector index | Inside the backend process (rebuilt at startup) |
| Postgres | Neon or Supabase free tier |
| Tracing | Langfuse Cloud, EU region |

Secrets (LLM API key, Langfuse keys, invite code, database URL) live in each platform's environment variables, never committed to the repo.

The VPS + docker-compose approach is noted as a deliberate later exercise, not adopted now.

## Consequences
- Backend cold starts on free tiers are an accepted risk (see `docs/design.md` § Risks) unless/until paying for always-on.
- Ephemeral backend disks are fine because the vector index is tiny and rebuilt at startup — this would need revisiting if the dataset grows enough that startup rebuild becomes slow.
- Moving to self-hosted infrastructure later is possible but out of scope until there's a specific reason (cost, control, or learning goal) to take it on.
