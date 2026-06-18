"""Provider-agnostic LLM client that streams text deltas.

Two backends, chosen by LLM_PROVIDER:
  * "anthropic" (default) -> official Anthropic SDK, model claude-opus-4-8.
  * "openai"             -> any OpenAI-compatible /chat/completions endpoint
                            (OpenAI, Together, Groq, Mistral, local vLLM, ...).

Both expose the same async generator interface: yield response text chunks.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .config import Settings


async def stream_answer(
    settings: Settings,
    system: str,
    messages: list[dict],
) -> AsyncIterator[str]:
    """Stream the assistant's reply as text chunks.

    `messages` is a list of {"role": "user"|"assistant", "content": str}.
    """
    if settings.llm_provider.lower() == "anthropic":
        async for chunk in _stream_anthropic(settings, system, messages):
            yield chunk
    else:
        async for chunk in _stream_openai(settings, system, messages):
            yield chunk


async def _stream_anthropic(
    settings: Settings, system: str, messages: list[dict]
) -> AsyncIterator[str]:
    from anthropic import AsyncAnthropic

    api_key = settings.anthropic_api_key or settings.llm_api_key
    client = AsyncAnthropic(api_key=api_key)

    # Streaming is the default for any potentially long output; .stream() also
    # protects against request timeouts on larger max_tokens.
    async with client.messages.stream(
        model=settings.llm_model,
        max_tokens=4096,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _stream_openai(
    settings: Settings, system: str, messages: list[dict]
) -> AsyncIterator[str]:
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "stream": True,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, read=120.0)) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
