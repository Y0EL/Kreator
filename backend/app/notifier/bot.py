from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.agents.script_pipeline import render_sources, rewrite_draft, run_full_generation
from app.config import get_settings
from app.db.enums import Decision, StoryStatus
from app.db.models import CandidateQueue, ResearchPack, Story
from app.db.session import SessionLocal
from app.export.document import build_docx, build_pdf
from app.logging import configure_logging, get_logger
from app.notifier.telegram import draft_keyboard, send_document, send_text

log = get_logger(__name__)
dp = Dispatcher()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "draft"


def _story_id(data: str) -> int:
    return int(data.split(":")[2])


async def _set_decision(story_id: int, decision: Decision, status: StoryStatus) -> None:
    async with SessionLocal() as session:
        cand = await session.scalar(
            select(CandidateQueue).where(CandidateQueue.story_id == story_id)
        )
        if cand:
            cand.decision = decision
            cand.status = status
            cand.decided_at = datetime.now(timezone.utc)
        story = await session.get(Story, story_id)
        if story:
            story.status = status
        await session.commit()


async def _generate_and_send(story_id: int, note: str | None = None) -> None:
    async with SessionLocal() as session:
        story = await session.get(Story, story_id)
        if story is None:
            await send_text("Cerita tidak ditemukan.")
            return
        if note:
            script = await rewrite_draft(session, story, note)
        else:
            script = await run_full_generation(session, story)
        pack = await session.scalar(
            select(ResearchPack).where(ResearchPack.story_id == story_id)
        )
        sources = await render_sources(session, story, pack)
        title = f"{story.title or 'Untitled'} (story {story_id})"
        meta = [
            f"Persona: {script.voice_persona}",
            f"Durasi target: sekitar {script.estimated_minutes} menit",
            f"Versi: v{script.version}",
        ]
        body = script.draft or ""
        version = script.version

    base = _slug(title)
    docx = build_docx(title, body, sources, meta)
    await send_document(
        docx,
        f"{base}.docx",
        caption=f"📄 Draft v{version}: {title}",
        reply_markup=draft_keyboard(story_id),
    )
    try:
        pdf = build_pdf(title, body, sources, meta)
        await send_document(pdf, f"{base}.pdf", caption="PDF buat dibaca")
    except Exception as e:
        log.warning("bot.pdf_failed", story_id=story_id, error=str(e))


async def _safe_generate(story_id: int, note: str | None = None) -> None:
    try:
        await _generate_and_send(story_id, note)
    except Exception as e:
        log.error("bot.generate_failed", story_id=story_id, error=str(e))
        await send_text(f"Gagal generate story {story_id}: {e}")


@dp.callback_query(F.data.startswith("act:approve:"))
async def on_approve(cb: CallbackQuery) -> None:
    story_id = _story_id(cb.data or "")
    await cb.answer("Approved. Lagi riset dan nulis draft, tunggu sebentar.")
    if cb.message:
        await cb.message.edit_text((cb.message.text or "") + "\n\n✅ Disetujui. Sedang digarap...")
    await _set_decision(story_id, Decision.approve, StoryStatus.approved)
    asyncio.create_task(_safe_generate(story_id))


@dp.callback_query(F.data.startswith("act:reject:"))
async def on_reject(cb: CallbackQuery) -> None:
    story_id = _story_id(cb.data or "")
    await _set_decision(story_id, Decision.reject, StoryStatus.scored)
    await cb.answer("Ditolak.")
    if cb.message:
        await cb.message.edit_text((cb.message.text or "") + "\n\n❌ Ditolak.")


@dp.callback_query(F.data.startswith("act:later:"))
async def on_later(cb: CallbackQuery) -> None:
    story_id = _story_id(cb.data or "")
    await _set_decision(story_id, Decision.later, StoryStatus.queued)
    await cb.answer("Disimpan untuk nanti.")
    if cb.message:
        await cb.message.edit_text((cb.message.text or "") + "\n\n⏳ Disimpan untuk nanti.")


@dp.callback_query(F.data.startswith("act:deep:"))
async def on_deep(cb: CallbackQuery) -> None:
    story_id = _story_id(cb.data or "")
    await cb.answer("Deep research dijalankan, sama seperti approve lalu generate.")
    if cb.message:
        await cb.message.edit_text((cb.message.text or "") + "\n\n🔍 Deep research...")
    await _set_decision(story_id, Decision.deep_research, StoryStatus.researching)
    asyncio.create_task(_safe_generate(story_id))


@dp.callback_query(F.data.startswith("draft:regen:"))
async def on_regen(cb: CallbackQuery) -> None:
    story_id = _story_id(cb.data or "")
    await cb.answer("Regenerate draft, tunggu sebentar.")
    asyncio.create_task(
        _safe_generate(story_id, note="versi sebelumnya kurang pas, tulis ulang lebih natural")
    )


@dp.callback_query(F.data.startswith("draft:ok:"))
async def on_ok(cb: CallbackQuery) -> None:
    await cb.answer("Sip, dipakai. 👍")


async def main() -> None:
    configure_logging()
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    log.info("bot.start_polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
