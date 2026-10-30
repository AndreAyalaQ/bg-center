# frontend

React + TypeScript chat UI. Not yet implemented — see `docs/design.md` and the root `CLAUDE.md` build plan.

Planned screens/components (per `docs/design.md` § API contract and § MVP scope):
- Invite-code gate (exchanges for a bearer token via `/api/auth`)
- Member strip (`/api/members`)
- Chat view streaming `/api/chat` over Server-Sent Events, with a plain `fetch` (no websockets)
- Sources display ("based on Miguel's profile")
- Thumbs up/down feedback (`/api/feedback`)

Deploys to Vercel/Netlify/Cloudflare Pages on push to `main` (ADR-0002).
