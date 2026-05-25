from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import Priority, StoryStatus
from app.db.models import CandidateQueue, RawItem, Story
from app.integrations import r2
from app.logging import get_logger
from app.pipeline import dedup, scoring
from app.pipeline.cleaner import clean_text, detect_language
from app.pipeline.enricher import enrich_story

log = get_logger(__name__)
_MIN_CLEAN_CHARS = 300


async def _unprocessed_raw_items(session: AsyncSession, limit: int) -> list[RawItem]:
    subq = select(Story.raw_item_id)
    return list(
        (
            await session.scalars(
                select(RawItem).where(RawItem.id.not_in(subq)).limit(limit)
            )
        ).all()
    )


def _load_raw_text(item: RawItem) -> str:
    if item.r2_key_raw:
        try:
            return r2.get_text(item.r2_key_raw)
        except Exception as e:
            log.warning("processor.r2_read_failed", raw_item_id=item.id, error=str(e))
    return item.raw_excerpt or ""


async def process_raw_item(session: AsyncSession, item: RawItem) -> Story | None:
    cleaned = clean_text(_load_raw_text(item))
    if len(cleaned) < _MIN_CLEAN_CHARS:
        log.info("processor.skip_short", raw_item_id=item.id)
        return None

    story = Story(
        raw_item_id=item.id,
        title=item.title,
        cleaned_text=cleaned,
        language=detect_language(cleaned),
        status=StoryStatus.cleaned,
    )
    session.add(story)
    await session.flush()

    enrich_story(story)
    novelty = await dedup.assign_cluster(session, story)
    score = scoring.compute_score(story, novelty=novelty)
    session.add(score)

    if story.is_primary and score.priority in (Priority.A, Priority.B):
        story.status = StoryStatus.queued
        session.add(
            CandidateQueue(story_id=story.id, status=StoryStatus.queued, priority=score.priority)
        )
    else:
        story.status = StoryStatus.duplicate if not story.is_primary else StoryStatus.scored
    return story


async def process_new(session: AsyncSession, limit: int = 200) -> int:
    items = await _unprocessed_raw_items(session, limit)
    count = 0
    for item in items:
        try:
            if await process_raw_item(session, item) is not None:
                count += 1
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error("processor.item_failed", raw_item_id=item.id, error=str(e))
    log.info("processor.done", created=count, scanned=len(items))
    return count
