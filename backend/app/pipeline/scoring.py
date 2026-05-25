from __future__ import annotations

import math
from datetime import datetime, timezone

from app.db.enums import Confidence, Priority
from app.db.models import Story, StoryScore

WEIGHTS: dict[str, float] = {
    "engagement": 0.20,
    "freshness": 0.10,
    "novelty": 0.20,
    "narrative_depth": 0.20,
    "horror_fit": 0.10,
    "reliability": 0.10,
    "audience_match": 0.10,
}

_HORROR_TOPICS = {"horor", "misteri", "legenda", "true_crime"}


def _engagement(story: Story) -> float:
    item = story.raw_item
    replies = (item.reply_count or 0) if item else 0
    views = (item.view_count or 0) if item else 0
    score = math.log10(1 + replies) / 3.0 + math.log10(1 + views) / 6.0
    return min(score, 1.0)


def _freshness(story: Story) -> float:
    item = story.raw_item
    posted = item.posted_at if item else None
    if not posted:
        return 0.4
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    days = (datetime.now(tz=timezone.utc) - posted).days
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.8
    if days <= 365:
        return 0.5
    return 0.3


def _narrative_depth(story: Story) -> float:
    tension = story.tension_score or 0.0
    minutes = story.estimated_minutes or 0
    length = min(len(story.cleaned_text) / 8000.0, 1.0)
    dur = min(minutes / 20.0, 1.0)
    return min(0.5 * tension + 0.25 * dur + 0.25 * length, 1.0)


def _horror_fit(story: Story) -> float:
    return 1.0 if (story.topic in _HORROR_TOPICS) else 0.3


def _reliability(story: Story) -> float:
    return {Confidence.high: 1.0, Confidence.medium: 0.6, Confidence.low: 0.3}.get(
        story.confidence, 0.4
    )


def compute_score(story: Story, novelty: float, audience_match: float = 0.5) -> StoryScore:
    comp = {
        "engagement": _engagement(story),
        "freshness": _freshness(story),
        "novelty": max(0.0, min(novelty, 1.0)),
        "narrative_depth": _narrative_depth(story),
        "horror_fit": _horror_fit(story),
        "reliability": _reliability(story),
        "audience_match": audience_match,
    }
    final = sum(WEIGHTS[k] * v for k, v in comp.items())
    return StoryScore(
        story_id=story.id,
        **comp,
        final_score=round(final, 4),
        priority=_priority(final, story),
    )


def _priority(final: float, story: Story) -> Priority:
    if not story.is_primary:
        return Priority.reject
    if final >= 0.75:
        return Priority.A
    if final >= 0.62:
        return Priority.B
    if final >= 0.5:
        return Priority.C
    return Priority.reject
