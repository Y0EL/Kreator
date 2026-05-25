from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CandidateQueue,
    CrawlJob,
    RawItem,
    ResearchPack,
    Script,
    Source,
    Story,
    StoryScore,
)
from app.logging import get_logger

log = get_logger(__name__)


async def purge_source(session: AsyncSession, source_id: int) -> str | None:
    src = await session.get(Source, source_id)
    if src is None:
        return None
    name = src.name
    raw_ids = list(
        (await session.scalars(select(RawItem.id).where(RawItem.source_id == source_id))).all()
    )
    if raw_ids:
        story_ids = list(
            (
                await session.scalars(select(Story.id).where(Story.raw_item_id.in_(raw_ids)))
            ).all()
        )
        if story_ids:
            for model in (StoryScore, CandidateQueue, ResearchPack, Script):
                await session.execute(delete(model).where(model.story_id.in_(story_ids)))
            await session.execute(delete(Story).where(Story.id.in_(story_ids)))
    await session.execute(delete(CrawlJob).where(CrawlJob.source_id == source_id))
    await session.execute(delete(RawItem).where(RawItem.source_id == source_id))
    await session.delete(src)
    await session.commit()
    log.info("source.purged", source_id=source_id, name=name)
    return name
