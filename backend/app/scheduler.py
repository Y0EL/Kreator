from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.crawler.runner import crawl_active_sources
from app.db.session import SessionLocal
from app.logging import get_logger
from app.notifier.telegram import send_digest
from app.pipeline.processor import process_new

log = get_logger(__name__)


async def run_collection() -> None:
    async with SessionLocal() as session:
        jobs = await crawl_active_sources(session)
    async with SessionLocal() as session:
        created = await process_new(session)
    log.info("schedule.collection", jobs=len(jobs), created=created)


async def run_digest_job() -> None:
    async with SessionLocal() as session:
        sent = await send_digest(session)
    log.info("schedule.digest", sent=sent)


def build_scheduler() -> AsyncIOScheduler:
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
    return scheduler
