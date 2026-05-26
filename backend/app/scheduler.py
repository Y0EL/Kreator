from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.crawler.runner import crawl_active_sources
from app.db.session import SessionLocal
from app.logging import get_logger
from app.notifier.telegram import send_digest, send_text
from app.pipeline.processor import process_new
from app.services import progress

log = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_collection() -> None:
    progress.start("crawl", "Mengumpulkan cerita")
    progress.step("Crawl sumber", 20)
    async with SessionLocal() as session:
        jobs = await crawl_active_sources(session)
    progress.step("Filter dan skor kandidat", 55)
    async with SessionLocal() as session:
        candidates = await process_new(session)
    new_items = sum(getattr(j, "items_new", 0) for j in jobs)
    sent = 0
    if candidates > 0:
        progress.step("Kirim kandidat ke Telegram", 85)
        async with SessionLocal() as session:
            sent = await send_digest(session, unsent_only=True)
    progress.done(f"{candidates} kandidat lolos filter")
    try:
        if candidates > 0:
            await send_text(
                f"🕷️ Crawl kelar. {len(jobs)} sumber, {new_items} item baru, "
                f"{candidates} kandidat lolos filter. Digest dikirim, tinggal approve."
            )
        else:
            await send_text(
                f"🕷️ Crawl kelar. {len(jobs)} sumber, {new_items} item baru, "
                "belum ada yang lolos filter."
            )
    except Exception:
        pass
    log.info("schedule.collection", jobs=len(jobs), candidates=candidates, sent=sent)


def status() -> dict:
    s = _scheduler
    tz = get_settings().tz
    now = datetime.now(ZoneInfo(tz))
    mode = "Crawl tiap 3 jam"
    jobs = []
    if s:
        for j in s.get_jobs():
            nr = getattr(j, "next_run_time", None)
            jobs.append({"id": j.id, "next_run": nr.isoformat() if nr else None})
    return {
        "scheduler_running": bool(s and s.running),
        "mode": mode,
        "tz": tz,
        "now": now.isoformat(),
        "jobs": jobs,
    }


def build_scheduler() -> AsyncIOScheduler:
    global _scheduler
    tz = get_settings().tz
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        run_collection,
        CronTrigger(hour="*/3", minute=0, timezone=tz),
        id="collection",
        max_instances=1,
        coalesce=True,
    )
    _scheduler = scheduler
    return scheduler
