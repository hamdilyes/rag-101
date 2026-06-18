# rag-101

A RAG application over a corpus of PDF files, with a chat UI styled after
claude.ai. Documents are processed locally (parsing, chunking, embedding) with
parallel computing and configurable resource limits. Only the generated
embeddings are pushed, never the source PDFs. Embeddings use a Qwen model from
HuggingFace, with a Qwen reranker at query time; any LLM API can be configured
via an env file.

> **Active development lives on the [`dev`](../../tree/dev) branch.**
> `main` is kept clean. Check out `dev` for the full code, setup, and docs.

```bash
git checkout dev
```
