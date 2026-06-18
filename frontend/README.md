# Frontend

Next.js (App Router) + Tailwind chat UI styled after claude.ai, including the
**"Salam Ostad"** greeting on the empty state. Streams answers from the backend
and shows the retrieved sources under each answer.

## Setup

```bash
npm install
cp .env.local.example .env.local   # optional; defaults to http://localhost:8000
```

## Run

Start the backend first (`cd ../backend && uv run rag-serve`), then:

```bash
npm run dev
# -> http://localhost:3000
```

Requests to `/backend/*` are proxied to the FastAPI server (set `BACKEND_URL`
in `.env.local` to change the target), so there is no CORS configuration to do
and SSE streaming works through the dev server.

## Look & feel

- Warm cream canvas, coral (clay) accent, serif display face — see
  `tailwind.config.ts` and `app/globals.css`.
- The greeting lives in `app/page.tsx` (`Salam Ostad`).
- Streaming, markdown rendering, and the collapsible **sources** panel are in
  `components/`.
