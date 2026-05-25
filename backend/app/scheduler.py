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
    progress.step("Crawl sumber", 25)
    async with SessionLocal() as session:
        jobs = await crawl_active_sources(session)
    progress.step("Memproses item baru", 70)
    async with SessionLocal() as session:
        created = await process_new(session)
    new_items = sum(getattr(j, "items_new", 0) for j in jobs)
    progress.done(f"{created} kandidat baru")
    try:
        await send_text(
            f"🕷️ Crawl kelar. {len(jobs)} sumber, {new_items} item baru, {created} kandidat baru."
        )
    except Exception:
        pass
    log.info("schedule.collection", jobs=len(jobs), created=created)


async def run_digest_job() -> None:
    async with SessionLocal() as session:
        sent = await send_digest(session)
    log.info("schedule.digest", sent=sent)


def status() -> dict:
    s = _scheduler
    tz = get_settings().tz
    now = datetime.now(ZoneInfo(tz))
    hour = now.hour
    if 1 <= hour < 10:
        mode = "Waktu approval"
    elif 10 <= hour < 22:
        mode = "Mengumpulkan cerita"
    else:
        mode = "Istirahat"
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
        CronTrigger(hour="10-21/2", minute=0, timezone=tz),
        id="collection",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_digest_job,
        CronTrigger(hour=1, minute=0, timezone=tz),
        id="digest",
        max_instances=1,
        coalesce=True,
    )
    _scheduler = scheduler
    return scheduler
