# frontend

React + TypeScript chat UI (Vite, React 19, oxlint). Talks to the backend over the four endpoints in `docs/design.md` § API contract.

## Layout

```
frontend/
├── src/
│   ├── api/
│   │   ├── types.ts      Wire types (camelCase, matching backend/app/api/schemas.py)
│   │   └── client.ts       authenticate(), getMembers(), sendFeedback(), streamChat()
│   ├── hooks/
│   │   └── useAuth.ts      Token state, persisted to localStorage
│   ├── components/
│   │   ├── InviteGate.tsx    Invite-code form
│   │   ├── MemberStrip.tsx    Member avatars (falls back to initials)
│   │   ├── ChatView.tsx        Message list + input, owns the streaming loop
│   │   └── MessageBubble.tsx    One message: content, sources, thumbs
│   └── App.tsx              Ties it together: InviteGate until authed, then the chat
├── .env.example
└── package.json
```

## SSE over plain `fetch`, not `EventSource`

`docs/design.md` requires SSE via plain `fetch` rather than WebSockets — and specifically not the browser's `EventSource` API, because `EventSource` can't send custom headers, so there'd be no way to attach the `Authorization: Bearer <token>` the API requires on every endpoint except `/api/auth`.

`client.ts`'s `streamChat()` is a hand-rolled async generator: it reads `response.body` as a `ReadableStream`, decodes chunks, and splits on the `event: <name>\ndata: <json>\n\n` format `app/api/routes.py`'s `_sse()` produces, yielding typed `{type: "token", token}` / `{type: "done", data}` events as they arrive.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
```

## Run

```bash
npm run dev
# -> http://localhost:5173
```

Needs the backend running too (`cd backend && .venv/bin/uvicorn app.main:app --reload`) and an `INVITE_CODE` set in the repo-root `.env` to actually log in.

## Checks

```bash
npx tsc -b        # type check
npm run lint      # oxlint
npm run build     # production build (tsc -b && vite build)
```

Deploys to Vercel/Netlify/Cloudflare Pages on push to `main` (ADR-0002) — not wired up yet (CLAUDE.md step 10).
