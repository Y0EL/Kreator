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


def web_search(query: str) -> str:
    s = get_settings()
    if s.tavily_api_key:
        try:
            out = _tavily_search(query, s.tavily_api_key)
            if out:
                return out
        except Exception as e:
            log.warning("llm.tavily_failed", error=str(e))
    return _openai_search(query)


def _tavily_search(query: str, key: str) -> str:
    import httpx

    r = httpx.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "query": query,
            "search_depth": "advanced",
            "max_results": 6,
            "include_answer": True,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    parts: list[str] = []
    if data.get("answer"):
        parts.append(str(data["answer"]))
    for it in data.get("results", []):
        title = it.get("title") or ""
        content = (it.get("content") or "")[:500]
        url = it.get("url") or ""
        parts.append(f"- {title}: {content} ({url})")
    return "\n".join(parts).strip()


def _openai_search(query: str) -> str:
    import litellm

    litellm.drop_params = True
    s = get_settings()
    messages = [
        {
            "role": "system",
            "content": (
                "Kamu peneliti fakta. Cari informasi terbaru dan akurat tentang kisah berikut "
                "dari web. Balas ringkas dalam Bahasa Indonesia, fokus ke fakta yang dapat "
                "diverifikasi seperti nama, tempat, kota, tanggal, tahun, dan kronologi nyata. "
                "Sebut sumber bila ada. Jangan mengarang."
            ),
        },
        {"role": "user", "content": query},
    ]
    try:
        resp = litellm.completion(
            model=s.web_search_model, messages=messages, api_key=s.openai_api_key
        )
        return resp.choices[0].message.content or ""  # type: ignore[union-attr,index]
    except Exception as e:
        log.warning("llm.web_search_failed", error=str(e))
        return ""


def count_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text or ""))
    except Exception:
        return max(1, len(text or "") // 4)


def complete_stream(
    *,
    system: str,
    user: str,
    tier: Tier = "quality",
    temperature: float = 0.8,
    on_progress: Any = None,
) -> str:
    import litellm

    litellm.drop_params = True
    s = get_settings()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    resp = litellm.completion(
        model=_route(tier),
        messages=messages,
        api_key=s.openai_api_key,
        temperature=temperature,
        stream=True,
    )
    parts: list[str] = []
    n = 0
    for chunk in resp:
        try:
            delta = chunk.choices[0].delta.content
        except Exception:
            delta = None
        if not delta:
            continue
        parts.append(delta)
        n += 1
        if on_progress and n % 16 == 0:
            try:
                on_progress("".join(parts))
            except Exception:
                pass
    text = "".join(parts)
    if on_progress:
        try:
            on_progress(text)
        except Exception:
            pass
    log.debug("llm.stream", tier=tier, chars=len(text))
    return text


def complete_json(*, system: str, user: str, tier: Tier = "cheap", **kw: Any) -> dict:
    raw = complete(system=system, user=user, tier=tier, json_mode=True, **kw)
    return _parse_json(raw)


def chat_raw(messages: list, tools: list | None = None, tier: Tier = "quality"):
    import litellm

    litellm.drop_params = True
    s = get_settings()
    kwargs: dict[str, Any] = {
        "model": _route(tier),
        "messages": messages,
        "api_key": s.openai_api_key,
        "temperature": 0.3,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    return litellm.completion(**kwargs)


def embed(texts: list[str]) -> list[list[float]]:
    import litellm

    litellm.drop_params = True
    s = get_settings()
    resp = litellm.embedding(
        model=s.llm_embedding_model, input=texts, api_key=s.openai_api_key
    )
    return [d["embedding"] for d in resp.data]  # type: ignore[union-attr]


def transcribe(audio_path: str) -> str:
    import litellm

    s = get_settings()
    with open(audio_path, "rb") as f:
        resp = litellm.transcription(model="whisper-1", file=f, api_key=s.openai_api_key)
    return getattr(resp, "text", "") or ""


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
