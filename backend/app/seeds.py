from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceStatus, SourceType
from app.db.models import Source
from app.logging import get_logger

log = get_logger(__name__)

WIKIPEDIA_SOURCE: dict = {
    "name": "Wikipedia Indonesia (Misteri & Legenda)",
    "type": SourceType.mediawiki,
    "base_url": "https://id.wikipedia.org",
    "parser_config": {
        "api_url": "https://id.wikipedia.org/w/api.php",
        "ignore_robots": True,
        "categories": [
            "Hantu Indonesia",
            "Legenda Indonesia",
            "Cerita rakyat Indonesia",
            "Makhluk legendaris Indonesia",
            "Mitologi Indonesia",
            "Kriminalitas di Indonesia",
        ],
        "limit": 6,
        "max_total": 24,
        "min_chars": 1200,
    },
    "crawl_interval_minutes": 720,
    "priority": 7,
}

SEED_SOURCES: list[dict] = [
    WIKIPEDIA_SOURCE,
    {
        "name": "Creepypasta Wiki (Fandom)",
        "type": SourceType.mediawiki,
        "base_url": "https://creepypasta.fandom.com",
        "parser_config": {
            "api_url": "https://creepypasta.fandom.com/api.php",
            "limit": 15,
            "min_chars": 1500,
        },
        "crawl_interval_minutes": 720,
        "priority": 8,
    },
    {
        "name": "Creepypasta.com",
        "type": SourceType.rss,
        "base_url": "https://www.creepypasta.com",
        "parser_config": {
            "feed_url": "https://www.creepypasta.com/feed/",
            "fetch_full": True,
            "max_items": 20,
        },
        "crawl_interval_minutes": 720,
        "priority": 7,
    },
    {
        "name": "CreepyFiles (Horor Indonesia)",
        "type": SourceType.rss,
        "base_url": "https://creepyfiles.com",
        "parser_config": {"feed_url": "https://creepyfiles.com/feed/", "fetch_full": True},
        "crawl_interval_minutes": 720,
        "priority": 6,
    },
    {
        "name": "True Crime Indonesia (OpenSERP)",
        "type": SourceType.search,
        "base_url": "openserp://google",
        "status": SourceStatus.paused,
        "parser_config": {
            "query": "kasus pembunuhan misterius indonesia",
            "engine": "google",
            "lang": "ID",
            "limit": 10,
            "min_chars": 800,
        },
        "crawl_interval_minutes": 1440,
        "priority": 7,
    },
    {
        "name": "True Crime International (OpenSERP)",
        "type": SourceType.search,
        "base_url": "openserp://google",
        "status": SourceStatus.paused,
        "parser_config": {
            "query": "disturbing unsolved true crime case",
            "engine": "google",
            "lang": "EN",
            "limit": 10,
            "min_chars": 800,
        },
        "crawl_interval_minutes": 1440,
        "priority": 6,
    },
]


async def ensure_default_sources(session: AsyncSession) -> int:
    created = 0
    for spec in (WIKIPEDIA_SOURCE,):
        exists = await session.scalar(select(Source.id).where(Source.name == spec["name"]))
        if exists:
            continue
        session.add(Source(**spec))
        created += 1
    if created:
        await session.commit()
        log.info("seed.defaults.done", created=created)
    return created


async def seed_sources(session: AsyncSession) -> int:
    created = 0
    for spec in SEED_SOURCES:
        exists = await session.scalar(select(Source.id).where(Source.name == spec["name"]))
        if exists:
            continue
        session.add(Source(**spec))
        created += 1
    await session.commit()
    log.info("seed.sources.done", created=created, total=len(SEED_SOURCES))
    return created
