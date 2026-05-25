from __future__ import annotations

from app.db.enums import Confidence, Priority
from app.db.models import RawItem, Story
from app.pipeline.scoring import compute_score


def _story(**kw) -> Story:
    story = Story(id=1, cleaned_text="x" * 6000, is_primary=True)
    story.raw_item = RawItem(reply_count=200, view_count=5000)
    story.topic = "horor"
    story.confidence = Confidence.high
    story.tension_score = 0.8
    story.estimated_minutes = 18
    for k, v in kw.items():
        setattr(story, k, v)
    return story


def test_strong_horror_story_high_priority():
    score = compute_score(_story(), novelty=0.9)
    assert score.final_score > 0.6
    assert score.priority in (Priority.A, Priority.B)


def test_duplicate_is_rejected():
    score = compute_score(_story(is_primary=False), novelty=0.0)
    assert score.priority == Priority.reject


def test_weak_story_low_priority():
    story = _story(
        topic="pengalaman_pribadi",
        confidence=Confidence.low,
        tension_score=0.1,
        estimated_minutes=5,
        cleaned_text="x" * 800,
    )
    story.raw_item = RawItem(reply_count=1, view_count=10)
    score = compute_score(story, novelty=0.2)
    assert score.final_score < 0.55
