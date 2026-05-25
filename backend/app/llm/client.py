from __future__ import annotations

import json
from typing import Any, Literal

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)
Tier = Literal["cheap", "quality"]


def _route(tier: Tier) -> str:
    s = get_settings()
    return s.llm_model_quality if tier == "quality" else s.llm_model_cheap


def complete(
    *,
    system: str,
    user: str,
    tier: Tier = "cheap",
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    import litellm

    litellm.drop_params = True
    s = get_settings()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    kwargs: dict[str, Any] = {
        "model": _route(tier),
        "messages": messages,
        "api_key": s.openai_api_key,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = litellm.completion(**kwargs)
    content = resp.choices[0].message.content  # type: ignore[union-attr,index]
    log.debug("llm.complete", tier=tier, chars=len(content or ""))
    return content or ""


def complete_json(*, system: str, user: str, tier: Tier = "cheap", **kw: Any) -> dict:
    raw = complete(system=system, user=user, tier=tier, json_mode=True, **kw)
    return _parse_json(raw)


def embed(texts: list[str]) -> list[list[float]]:
    import litellm

    litellm.drop_params = True
    s = get_settings()
    resp = litellm.embedding(
        model=s.llm_embedding_model, input=texts, api_key=s.openai_api_key
    )
    return [d["embedding"] for d in resp.data]  # type: ignore[union-attr]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise
