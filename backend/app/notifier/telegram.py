from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import StoryStatus
from app.db.models import CandidateQueue, RawItem, Story, StoryScore
from app.logging import get_logger

log = get_logger(__name__)
_API = "https://api.telegram.org/bot{token}/{method}"


async def _post(method: str, payload: dict) -> dict:
    s = get_settings()
    url = _API.format(token=s.telegram_bot_token, method=method)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload)
        return r.json()


def _decision_keyboard(story_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"act:approve:{story_id}"},
                {"text": "❌ Reject", "callback_data": f"act:reject:{story_id}"},
            ],
            [
                {"text": "⏳ Later", "callback_data": f"act:later:{story_id}"},
                {"text": "🔍 Deep Research", "callback_data": f"act:deep:{story_id}"},
            ],
        ]
    }


def draft_keyboard(story_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "👍 Oke, pakai ini", "callback_data": f"draft:ok:{story_id}"},
                {"text": "🔄 Regenerate", "callback_data": f"draft:regen:{story_id}"},
            ]
        ]
    }


def _val(x: object) -> str:
    if x is None:
        return "-"
    return str(getattr(x, "value", x))


def _domain(url: str | None) -> str:
    if not url:
        return "-"
    return urlsplit(url).netloc or url


def _format_candidate(story: Story, score: StoryScore | None, source_url: str | None) -> str:
    prio = _val(score.priority) if score else "-"
    fs = round(score.final_score, 2) if score else "-"
    conf = _val(story.confidence)
    dur = story.estimated_minutes or "-"
    topic = story.topic or "-"
    summary = html.escape((story.summary or "")[:420])
    title = html.escape(story.title or "Tanpa judul")
    return (
        f"🔥 <b>{title}</b>\n"
        f"📊 Skor {fs} . Prioritas {prio} . Confidence {conf}\n"
        f"⏱ sekitar {dur} menit . 🏷 {topic}\n"
        f"🔗 Sumber: {html.escape(_domain(source_url))}\n\n"
        f"{summary}"
    )


async def send_document(
    file_bytes: bytes, filename: str, caption: str = "", reply_markup: dict | None = None
) -> dict:
    s = get_settings()
    url = _API.format(token=s.telegram_bot_token, method="sendDocument")
    data = {"chat_id": s.telegram_group_chat_id, "caption": caption[:1000]}
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup)
    files = {"document": (filename, file_bytes)}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, data=data, files=files)
        return r.json()


async def send_text(text: str) -> dict:
    s = get_settings()
    return await _post(
        "sendMessage",
        {"chat_id": s.telegram_group_chat_id, "text": text, "disable_notification": True},
    )


async def send_digest(session: AsyncSession, limit: int = 10) -> int:
    s = get_settings()
    rows = (
        await session.execute(
            select(Story, StoryScore, RawItem.source_url)
            .join(StoryScore, StoryScore.story_id == Story.id)
            .join(CandidateQueue, CandidateQueue.story_id == Story.id)
            .join(RawItem, RawItem.id == Story.raw_item_id)
            .where(CandidateQueue.status == StoryStatus.queued)
            .order_by(StoryScore.final_score.desc())
            .limit(limit)
        )
    ).all()
    if not rows:
        await send_text("Belum ada kandidat untuk digest.")
        return 0

    await send_text(f"📋 Digest: {len(rows)} kandidat teratas. Pilih lewat tombol di tiap cerita.")
    for story, score, source_url in rows:
        resp = await _post(
            "sendMessage",
            {
                "chat_id": s.telegram_group_chat_id,
                "text": _format_candidate(story, score, source_url),
                "parse_mode": "HTML",
                "reply_markup": _decision_keyboard(story.id),
                "disable_notification": True,
            },
        )
        if resp.get("ok"):
            cand = await session.scalar(
                select(CandidateQueue).where(CandidateQueue.story_id == story.id)
            )
            if cand:
                cand.telegram_message_id = resp["result"]["message_id"]
                cand.sent_in_digest_at = datetime.now(timezone.utc)
        else:
            log.error("digest.send_failed", story_id=story.id, resp=resp)
    await session.commit()
    log.info("digest.sent", count=len(rows))
    return len(rows)
