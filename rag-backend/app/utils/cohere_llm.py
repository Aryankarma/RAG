"""Helpers for Cohere Python SDK v5+ (Chat API); optional fallback for older clients."""

from __future__ import annotations

from typing import Any


def extract_chat_text(response: Any) -> str:
    """Normalize assistant text from ``client.chat(...)`` across response shapes."""
    if response is None:
        return ""
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()
    msg = getattr(response, "message", None)
    if msg is None:
        return ""
    content = getattr(msg, "content", None)
    if not content:
        return ""
    first = content[0]
    if isinstance(first, dict):
        return str(first.get("text", "")).strip()
    piece = getattr(first, "text", None)
    if piece:
        return str(piece).strip()
    return str(first).strip()


def cohere_generate_text(
    client: Any,
    prompt: str,
    *,
    model: str = "command-r-plus-08-2024",
    max_tokens: int = 500,
    temperature: float = 0.1,
) -> str:
    """Text completion: Chat API (v5+), with ``message=`` and legacy ``generate`` fallbacks."""
    chat = getattr(client, "chat", None)
    if callable(chat):
        try:
            response = chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return extract_chat_text(response)
        except TypeError:
            response = chat(
                message=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return extract_chat_text(response)

    gen = getattr(client, "generate", None)
    if callable(gen):
        r = gen(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        generations = getattr(r, "generations", None) or []
        if generations:
            g0 = generations[0]
            t = getattr(g0, "text", None)
            if t:
                return str(t).strip()
    raise RuntimeError("Cohere client supports neither chat() nor generate()")
