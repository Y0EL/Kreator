from __future__ import annotations

from app.db.enums import Confidence
from app.db.models import Story
from app.llm import client
from app.llm.prompts import ENRICH_SYSTEM, ENRICH_USER
from app.logging import get_logger

log = get_logger(__name__)

_MAX_CHARS = 12000


def enrich_story(story: Story) -> dict | None:
    text = story.cleaned_text[:_MAX_CHARS]
    try:
        data = client.complete_json(
            system=ENRICH_SYSTEM, user=ENRICH_USER.format(text=text), tier="cheap", temperature=0.3
        )
    except Exception as e:
        log.error("enrich.failed", story_id=getattr(story, "id", None), error=str(e))
        return None

    story.summary = data.get("summary")
    story.topic = data.get("topic")
    story.subtopics = data.get("subtopics") or []
    story.entities = data.get("entities") or {}
    story.timeline = data.get("timeline") or []
    story.tension_score = _as_float(data.get("tension_score"))
    story.estimated_minutes = _as_int(data.get("estimated_minutes"))
    story.confidence = _as_confidence(data.get("confidence"))

    try:
        story.embedding = client.embed([text])[0]
    except Exception as e:
        log.warning("enrich.embed_failed", error=str(e))

    vs = _as_int(data.get("viral_score")) or 0
    return {
        "viral_score": max(0, min(vs, 100)),
        "viral_label": data.get("viral_label"),
        "hook": data.get("viral_hook"),
        "reasons": data.get("viral_reasons") or [],
        "where_from": data.get("where_from"),
    }


def _as_float(v: object) -> float | None:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_int(v: object) -> int | None:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_confidence(v: object) -> Confidence | None:
    if isinstance(v, str) and v.lower() in Confidence._value2member_map_:
        return Confidence(v.lower())
    return None
