# Backend (RAG API)

FastAPI server that loads the committed embeddings index, embeds the query with
**Qwen3-Embedding**, runs cosine vector search, reranks with **Qwen3-Reranker**,
and streams an answer from a provider-agnostic LLM (Claude by default).

## Setup

```bash
uv sync
```

Configuration is read from the repo-root `.env` (copy `../.env.example`). Set at
least `ANTHROPIC_API_KEY` (or switch `LLM_PROVIDER=openai` and set
`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`).

## Run

The processing pipeline must have produced `../data/index/` first.

```bash
uv run rag-serve
# -> http://localhost:8000
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Index/model status. |
| `POST` | `/api/chat` | SSE stream of the answer. Body: `{ "message": str, "history": [...] }`. |

`/api/chat` emits `data: {json}\n\n` frames, each with a `type`:
`sources` (retrieved chunks), `delta` (text), `error`, `done`.

## Swapping the LLM

`LLM_PROVIDER=anthropic` uses the official Anthropic SDK (default model
`claude-opus-4-8`). `LLM_PROVIDER=openai` targets any OpenAI-compatible
`/chat/completions` endpoint — point `LLM_BASE_URL` at OpenAI, Together, Groq,
Mistral, or a local vLLM/llama.cpp server, set `LLM_API_KEY` and `LLM_MODEL`.

If the reranker model fails to load, the server logs a warning and falls back to
vector-only ranking.
