# rag-101

Chat with your own PDF documents through a UI styled after claude.ai. You drop
PDFs into a folder, run a one-time local processing step that turns them into
embeddings, then launch the app and ask questions. Answers are grounded in your
documents and show their sources.

Only the generated embeddings are committed to git, never the source PDFs.
Embeddings use a small HuggingFace model (`BAAI/bge-small-en-v1.5`); an optional
cross-encoder reranker is available but off by default. The chat answer comes
from an LLM you configure (OpenAI-compatible by default, e.g. OpenAI).

> Releases are tagged on `main`; active development continues on `dev`.

---

## What you need first (one time)

| Tool | Why | Install |
| --- | --- | --- |
| [`uv`](https://docs.astral.sh/uv/) | runs the Python parts (processing + backend) | `winget install astral-sh.uv` (Windows) or see the uv site |
| [Node.js 18+](https://nodejs.org) | runs the web UI | from nodejs.org |
| An LLM API key | generates the answers | e.g. an Anthropic key for Claude |

You do not need to install Python yourself; `uv` handles it.

---

## The whole flow at a glance

```
1. Configure .env         (your LLM API key)
2. Put PDFs in corpus/
3. Pick local settings     (processing/config.yaml)
4. Run processing          -> creates data/index/      (one time per corpus)
5. Start the backend       -> http://localhost:8000
6. Start the UI            -> http://localhost:3000     <-- this is the app
```

Steps 1 to 4 are done once (and again only when you change the documents).
Steps 5 and 6 are what you do every time you want to use the app.

---

## Step 1. Configure your LLM key

From the repo root, copy the example env file and edit it:

```bash
cp .env.example .env
```

Open `.env` and set your key. Default is an OpenAI-compatible provider:

```ini
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5.4-nano-2026-03-17
```

`LLM_BASE_URL` can point at any OpenAI-compatible endpoint (OpenAI, Together,
Groq, Mistral, or a local vLLM/llama.cpp server). See `.env.example`.

---

## Step 2. Put your documents in `corpus/`

Copy any number of `.pdf` files into the `corpus/` folder. Subfolders are fine.

The PDFs are never committed to git, so this folder stays private to your
machine.

---

## Step 3. Pick settings for your machine

Open [`processing/config.yaml`](processing/config.yaml). The defaults are safe.
The settings you may want to change:

| Setting | What it does | Default |
| --- | --- | --- |
| `resources.max_workers` | Parallel workers for parsing/chunking. `auto` uses your cores and RAM budget. | `auto` |
| `resources.max_ram_gb` | RAM budget for the parse/chunk stage and transient buffers. | `1.0` |
| `resources.embed_batch_size` | Bigger is faster but uses more memory. | `32` |
| `embedding.device` | `auto` picks GPU if you have one (`cuda`), else `cpu`. | `auto` |

Memory note: the embedding model (`BAAI/bge-small-en-v1.5`) is small (~130 MB
weights), so peak memory during processing stays well under 1 GB.

---

## Step 4. Run the processing (one time)

```bash
cd processing
uv sync          # first time only: installs the Python dependencies
uv run rag-process
cd ..
```

What happens: it parses every PDF, splits the text into chunks, downloads the
embedding model on first run (`BAAI/bge-small-en-v1.5`, ~130 MB, cached
afterward in `.hf_cache/`), embeds every chunk, and writes the index to
`data/index/`.

How long: fast. The small model downloads in seconds and embeds a handful of
typical PDFs in well under a minute on CPU. A GPU makes
embedding much faster.

It is resilient by design: a broken page, a broken PDF, or an odd chunk is
skipped and logged, never crashing the run. You will see progress like:

```
Found 4 PDF(s). Using 7 worker(s), RAM budget 1.0 GB.
  [1/4] Biology - Wikipedia.pdf: 38 chunks
  ...
Embedding on device=cpu, dim=1024 ...
  [embed] 812/812 chunks
Wrote index to .../data/index

Done: {'documents': 4, 'chunks': 812, 'embedded': 812, 'skipped': 0, 'dim': 1024}
```

### How do I know it is ready?

The index exists when `data/index/` contains three files:

```bash
ls data/index
# chunks.jsonl   embeddings.npy   meta.json
```

`meta.json` tells you how many chunks were embedded:

```bash
cat data/index/meta.json
```

If you see those files and a non-zero `count`, processing is done and the corpus
is ready to query.

---

## Step 5. Start the backend (the answer engine)

In a terminal:

```bash
cd backend
uv sync          # first time only
uv run rag-serve
```

It serves at `http://localhost:8000`. It loads the embedding model
(`BAAI/bge-small-en-v1.5`) to embed your questions. The reranker is off by
default; if you enable it, the cross-encoder downloads on first query.

### How do I know it is ready?

Open `http://localhost:8000/api/health` in a browser, or:

```bash
curl http://localhost:8000/api/health
```

You want to see `"ready": true` and a non-zero `"chunks"` count:

```json
{ "ready": true, "chunks": 259, "embedding_model": "BAAI/bge-small-en-v1.5",
  "llm_provider": "openai", "llm_model": "gpt-5.4-nano-2026-03-17" }
```

If `"ready": false`, the index was not found; re-check Step 4.

Leave this terminal running.

---

## Step 6. Start the UI (the app)

In a second terminal:

```bash
cd frontend
npm install      # first time only
npm run dev
```

When it prints `Ready`, open the app here:

## 👉 http://localhost:3000

You will be greeted with **Salam Ostad**. Type a question about your documents
and the answer streams in, with the source passages shown beneath it.

- **New chat** (top of the sidebar) erases the current conversation and starts
  fresh. The app keeps a single conversation; the whole conversation is sent as
  context on every message.
- If the answer engine is unreachable or has no key, the chat shows
  "Our LLM is currently offline" instead of crashing.

---

## Updating the documents later

1. Add or remove PDFs in `corpus/`.
2. Re-run Step 4 (`cd processing && uv run rag-process`). It rewrites
   `data/index/`.
3. Restart the backend (Step 5) so it loads the new index.

---

## What gets pushed to git

| Pushed | Not pushed |
| --- | --- |
| `data/index/` (embeddings + chunk text + metadata) | `corpus/` (your raw PDFs) |
| All source code and config | `.env` (your keys) |
| | `.hf_cache/` (downloaded models), `node_modules/`, build output |

This is the point of the project: a teammate can clone, set their own `.env`,
start the backend and UI, and query your corpus without ever receiving the
original PDFs.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| UI shows "Our LLM is currently offline" | Backend not running, or no/invalid API key in `.env`. Start the backend (Step 5) and check `.env`. |
| `/api/health` shows `"ready": false` | No index. Run processing (Step 4) and confirm `data/index/` has three files. |
| Processing exits saying the model could not load | No internet / HuggingFace access on first run. Reconnect and re-run; parsing already succeeded. |
| Embedding feels slow | It runs on CPU by default. Set `embedding.device: cuda` in `processing/config.yaml` if you have an NVIDIA GPU. |
| Port already in use | Change `BACKEND_PORT` in `.env`, or run the UI on another port with `npm run dev -- -p 3001`. |

Per-component details live in [`processing/`](processing/README.md),
[`backend/`](backend/README.md), and [`frontend/`](frontend/README.md).
