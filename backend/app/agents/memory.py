from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.models import Conversation
from app.db.session import SessionLocal
from app.llm import client
from app.logging import get_logger

log = get_logger(__name__)

RECENT_KEEP = 16
COMPACT_THRESHOLD = 30


async def load_history(chat_id: int) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.scalars(
                select(Conversation).where(Conversation.chat_id == chat_id).order_by(Conversation.id)
            )
        ).all()
    history: list[dict] = []
    summary = next((r for r in rows if r.role == "summary"), None)
    if summary:
        history.append({"role": "system", "content": "[memori percakapan] " + summary.content})
    history.extend(
        {"role": r.role, "content": r.content} for r in rows if r.role != "summary"
    )
    return history


async def append_turn(chat_id: int, role: str, content: str) -> None:
    async with SessionLocal() as session:
        session.add(Conversation(chat_id=chat_id, role=role, content=content[:8000]))
        await session.commit()


async def maybe_compact(chat_id: int) -> None:
    async with SessionLocal() as session:
        rows = (
            await session.scalars(
                select(Conversation).where(Conversation.chat_id == chat_id).order_by(Conversation.id)
            )
        ).all()
        turns = [r for r in rows if r.role != "summary"]
        if len(turns) <= COMPACT_THRESHOLD:
            return
        summary_row = next((r for r in rows if r.role == "summary"), None)
        old = turns[:-RECENT_KEEP]
        prev = summary_row.content if summary_row else ""
        convo = prev + "\n" + "\n".join(f"{r.role}: {r.content}" for r in old)
        try:
            summary = await asyncio.to_thread(
                client.complete,
                system="Ringkas percakapan ini jadi catatan konteks singkat: poin penting, "
                "keputusan, preferensi user. Maksimal 8 kalimat, Bahasa Indonesia.",
                user=convo[:12000],
                tier="cheap",
            )
        except Exception as e:
            log.warning("memory.compact_failed", error=str(e))
            return
        for r in old:
            await session.delete(r)
        if summary_row:
            summary_row.content = summary
        else:
            session.add(Conversation(chat_id=chat_id, role="summary", content=summary))
        await session.commit()
        log.info("memory.compacted", chat_id=chat_id, removed=len(old))
