"""Subject-model API client (OpenRouter only).

Distinct from `judge.py` so contributors can swap judges/subjects
independently. Both go through OpenRouter; both take the same API
key from $OPENROUTER_API_KEY.
"""
from __future__ import annotations

import httpx


OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def call_subject(
    *,
    route: str,
    system: str,
    messages: list[dict],
    api_key: str,
    http: httpx.AsyncClient,
    max_tokens: int = 1024,
    temperature: float = 0.85,
) -> str:
    """Run the subject model on (system, messages). Returns plain text."""
    msgs = [{"role": "system", "content": system}, *messages]
    r = await http.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": route,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=180.0,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]
