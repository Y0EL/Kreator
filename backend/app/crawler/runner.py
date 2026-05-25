from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crawler.adapters import get_adapter
from app.crawler.request_manager import RequestManager
from app.crawler.types import RawItemData
from app.crawler.validator import validate
from app.db.enums import CrawlJobStatus, SourceStatus, SourceType
from app.db.models import CrawlJob, RawItem, Source
from app.integrations import r2
from app.logging import get_logger
from app.util.hashing import content_hash

log = get_logger(__name__)


async def _hash_exists(session: AsyncSession, raw_hash: str) -> bool:
    res = await session.scalar(select(RawItem.id).where(RawItem.raw_hash == raw_hash))
    return res is not None


async def _persist_item(session: AsyncSession, source: Source, item: RawItemData) -> bool:
    ok, reason = validate(item)
    if not ok:
        log.info("crawl.item.invalid", source_id=source.id, url=item.source_url, reason=reason)
        return False

    raw_hash = content_hash(item.raw_text)
    if await _hash_exists(session, raw_hash):
        return False

    key_txt = r2.raw_key(source.id, raw_hash, "txt")
    r2.put_text(key_txt, item.raw_text)
    if item.raw_html:
        r2.put_text(
            r2.raw_key(source.id, raw_hash, "html"), item.raw_html, "text/html; charset=utf-8"
        )

    session.add(
        RawItem(
            source_id=source.id,
            source_url=item.source_url,
            title=item.title,
            author_name=item.author_name,
            posted_at=item.posted_at,
            crawled_at=datetime.now(tz=timezone.utc),
            r2_key_raw=key_txt,
            raw_hash=raw_hash,
            raw_excerpt=item.raw_text[:2000],
            reply_count=item.reply_count,
            view_count=item.view_count,
            media_links=item.media_links,
        )
    )
    return True


async def crawl_source(session: AsyncSession, source: Source) -> CrawlJob:
    settings = get_settings()
    job = CrawlJob(
        source_id=source.id,
        status=CrawlJobStatus.running,
        started_at=datetime.now(tz=timezone.utc),
    )
    session.add(job)
    await session.flush()

    found = new = 0
    try:
        async with RequestManager() as rm:
            adapter = get_adapter(source, rm)
            async for item in adapter.crawl():
                found += 1
                try:
                    if await _persist_item(session, source, item):
                        new += 1
                except Exception as e:
                    log.warning("crawl.item.error", source_id=source.id, error=str(e))
        job.status = CrawlJobStatus.success
        source.consecutive_errors = 0
        source.last_crawled_at = datetime.now(tz=timezone.utc)
    except Exception as e:
        job.status = CrawlJobStatus.failed
        job.error = str(e)[:2000]
        source.consecutive_errors += 1
        if source.consecutive_errors >= settings.crawl_source_error_threshold:
            source.status = SourceStatus.disabled
            log.error("crawl.source.auto_disabled", source_id=source.id)
        log.error("crawl.job.failed", source_id=source.id, error=str(e))

    job.items_found = found
    job.items_new = new
    job.finished_at = datetime.now(tz=timezone.utc)
    log.info("crawl.job.done", source_id=source.id, status=job.status, found=found, new=new)
    return job


async def crawl_active_sources(session: AsyncSession) -> list[CrawlJob]:
    sources = (
        await session.scalars(
            select(Source).where(
                Source.status == SourceStatus.active,
                Source.type != SourceType.submission,
            )
        )
    ).all()
    jobs = []
    for source in sources:
        jobs.append(await crawl_source(session, source))
        await session.commit()
    return jobs
