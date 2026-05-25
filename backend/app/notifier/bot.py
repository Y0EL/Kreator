from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy import select

from app.agents.admin_agent import run_admin_agent
from app.agents.delivery import generate_and_deliver
from app.config import get_settings
from app.db.enums import Decision, StoryStatus
from app.db.models import CandidateQueue, Story
from app.db.session import SessionLocal
from app.llm import client
from app.logging import configure_logging, get_logger
from app.notifier.telegram import send_text
from app.util.textfix import sanitize_script

log = get_logger(__name__)
dp = Dispatcher()
_BOT_USERNAME = "Y0ELBOT"


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


async def _safe_generate(story_id: int, note: str | None = None) -> None:
    try:
        await generate_and_deliver(story_id, note)
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


def _mentioned(msg: Message) -> bool:
    if f"@{_BOT_USERNAME}".lower() in (msg.text or "").lower():
        return True
    reply = msg.reply_to_message
    return bool(reply and reply.from_user and reply.from_user.is_bot)


async def _is_for_bot(text: str) -> bool:
    try:
        ans = await asyncio.to_thread(
            client.complete,
            system="Tentukan: pesan ini ditujukan ke asisten bot admin (perintah, pertanyaan, "
            "minta data/aksi/saran soal sistem)? Atau cuma obrolan iseng antar orang? "
            "Jawab HANYA satu kata: YA atau TIDAK.",
            user=text,
            tier="cheap",
            temperature=0,
        )
        return ans.strip().upper().startswith("YA")
    except Exception as e:
        log.warning("bot.gate_failed", error=str(e))
        return False


async def _send_reply(msg: Message, text: str) -> None:
    clean = sanitize_script(text)[:4000]
    try:
        await msg.reply(clean, parse_mode="HTML")
    except Exception as e:
        log.warning("bot.html_reply_failed", error=str(e))
        await msg.reply(clean)


async def _plain_chat(text: str) -> str:
    return await asyncio.to_thread(
        client.complete,
        system="Lo chatbot santai buat grup, ngobrol akrab pakai bahasa sehari-hari, jangan "
        "kaku, jangan pakai 'saya/anda'. Jawab singkat. Lo ga punya akses admin apa pun.",
        user=text,
        tier="cheap",
    )


@dp.message(F.text)
async def on_message(msg: Message) -> None:
    text_raw = msg.text or ""
    owner_id = get_settings().owner_telegram_id
    is_owner = bool(msg.from_user and owner_id and msg.from_user.id == owner_id)
    is_private = msg.chat.type == "private"

    if not (is_private or _mentioned(msg)):
        if is_owner:
            if not await _is_for_bot(text_raw):
                return
        else:
            return

    text = text_raw.replace(f"@{_BOT_USERNAME}", "").strip()
    if not text:
        return
    try:
        async with ChatActionSender.typing(bot=msg.bot, chat_id=msg.chat.id):
            reply = (
                await run_admin_agent(msg.chat.id, text)
                if is_owner
                else await _plain_chat(text)
            )
    except Exception as e:
        log.error("bot.message_failed", error=str(e))
        reply = "Waduh error pas ngeproses, coba lagi ya. 😵"
    await _send_reply(msg, reply)


async def main() -> None:
    configure_logging()
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    log.info("bot.start_polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
