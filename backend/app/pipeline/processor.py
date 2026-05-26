from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import Decision, Priority, StoryStatus
from app.db.models import CandidateQueue, RawItem, Story, StoryPitch, StoryScore
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
    raw = await asyncio.to_thread(_load_raw_text, item)
    cleaned = clean_text(raw)
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

    pitch = await asyncio.to_thread(enrich_story, story)
    novelty = await dedup.assign_cluster(session, story)
    score = scoring.compute_score(story, novelty=novelty)
    session.add(score)

    if story.is_primary and score.priority in (Priority.A, Priority.B):
        story.status = StoryStatus.queued
        session.add(
            CandidateQueue(story_id=story.id, status=StoryStatus.queued, priority=score.priority)
        )
        if pitch:
            session.add(
                StoryPitch(
                    story_id=story.id,
                    viral_score=pitch["viral_score"],
                    viral_label=pitch["viral_label"],
                    hook=pitch["hook"],
                    reasons=pitch["reasons"],
                    where_from=pitch["where_from"],
                )
            )
    else:
        story.status = StoryStatus.duplicate if not story.is_primary else StoryStatus.scored
    return story


async def process_new(session: AsyncSession, limit: int = 200) -> int:
    items = await _unprocessed_raw_items(session, limit)
    stories = 0
    candidates = 0
    for item in items:
        try:
            story = await process_raw_item(session, item)
            if story is not None:
                stories += 1
                if story.status == StoryStatus.queued:
                    candidates += 1
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error("processor.item_failed", raw_item_id=item.id, error=str(e))
    log.info("processor.done", candidates=candidates, stories=stories, scanned=len(items))
    return candidates


async def rescore_existing(session: AsyncSession, limit: int = 2000) -> int:
    rows = (
        await session.execute(
            select(Story, StoryScore)
            .join(StoryScore, StoryScore.story_id == Story.id)
            .limit(limit)
        )
    ).all()
    queued = 0
    for story, sc in rows:
        comp = {
            "engagement": sc.engagement,
            "freshness": sc.freshness,
            "novelty": sc.novelty,
            "narrative_depth": sc.narrative_depth,
            "horror_fit": sc.horror_fit,
            "reliability": sc.reliability,
            "audience_match": sc.audience_match,
        }
        has_eng = (sc.engagement or 0) > 0
        final = scoring.weighted_final(comp, has_eng)
        sc.final_score = final
        priority = scoring._priority(final, story)
        sc.priority = priority
        if story.is_primary and priority in (Priority.A, Priority.B):
            cand = await session.scalar(
                select(CandidateQueue).where(CandidateQueue.story_id == story.id)
            )
            if cand is None:
                story.status = StoryStatus.queued
                session.add(
                    CandidateQueue(
                        story_id=story.id, status=StoryStatus.queued, priority=priority
                    )
                )
                queued += 1
            elif cand.decision == Decision.pending and cand.status != StoryStatus.queued:
                cand.status = StoryStatus.queued
                cand.priority = priority
                story.status = StoryStatus.queued
                queued += 1
        await session.commit()
    log.info("processor.rescored", count=len(rows), queued=queued)
    return queued
