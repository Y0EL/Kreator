from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.delivery import generate_and_deliver
from app.config import get_settings
from app.crawler.runner import crawl_active_sources
from app.db.enums import Decision, SourceStatus, SourceType, StoryStatus
from app.db.models import (
    CandidateQueue,
    RawItem,
    ResearchPack,
    Script,
    Source,
    Story,
    StoryPitch,
    StoryScore,
)
from app.db.session import SessionLocal, get_session
from app.logging import get_logger
from app.notifier.telegram import send_digest, send_text
from app.pipeline.processor import process_new, rescore_existing
from app.scheduler import status as scheduler_status
from app.services import progress
from app.services.sources import purge_source
from app.services.youtube_ingest import ingest_youtube

log = get_logger(__name__)


def require_dashboard(authorization: str | None = Header(default=None)) -> None:
    token = get_settings().dashboard_token
    if not token or authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="unauthorized")


router = APIRouter(prefix="/api", dependencies=[Depends(require_dashboard)])


def _val(x: object):
    return getattr(x, "value", x) if x is not None else None


async def _bg_generate(story_id: int, note: str | None = None, web_search: bool = False) -> None:
    progress.start("draft", f"Story {story_id}")
    progress.step("Menyiapkan draft", 30, story_id=story_id)
    try:
        await generate_and_deliver(story_id, note, web_search=web_search)
    except Exception as e:
        progress.fail(str(e))
        log.error("api.generate_failed", story_id=story_id, error=str(e))


async def _bg_ingest(
    video: str, target_minutes: int | None = None, web_search: bool = False
) -> None:
    progress.start("youtube", video)
    try:
        await ingest_youtube(video, target_minutes, web_search=web_search)
    except Exception as e:
        progress.fail(str(e))
        log.error("api.ingest_failed", video=video, error=str(e))


async def _bg_action(name: str) -> None:
    labels = {
        "cycle": "Crawl penuh",
        "crawl": "Crawl sumber",
        "process": "Memproses item",
        "digest": "Kirim digest",
        "rescore": "Skor ulang bahan",
    }
    progress.start(name, labels.get(name, name))
    progress.step(labels.get(name, name), 20)
    try:
        async with SessionLocal() as session:
            if name == "cycle":
                jobs = await crawl_active_sources(session)
                new_items = sum(getattr(j, "items_new", 0) for j in jobs)
                progress.step("Filter dan skor kandidat", 60)
                candidates = await process_new(session)
                sent = 0
                if candidates > 0:
                    progress.step("Kirim kandidat ke Telegram", 88)
                    sent = await send_digest(session, unsent_only=True)
                progress.done(f"{candidates} kandidat baru")
                await send_text(
                    f"Crawl penuh kelar. {len(jobs)} sumber, {new_items} item baru, "
                    f"{candidates} kandidat baru, {sent} dikirim."
                )
            elif name == "crawl":
                jobs = await crawl_active_sources(session)
                new_items = sum(getattr(j, "items_new", 0) for j in jobs)
                progress.done(f"{len(jobs)} sumber, {new_items} item baru")
                await send_text(f"Crawl kelar. {len(jobs)} sumber, {new_items} item baru.")
            elif name == "process":
                created = await process_new(session)
                progress.done(f"{created} kandidat baru")
            elif name == "digest":
                sent = await send_digest(session)
                progress.done(f"{sent} kandidat dikirim")
            elif name == "rescore":
                queued = await rescore_existing(session)
                progress.done(f"{queued} kandidat baru dari bahan lama")
                await send_text(f"Skor ulang kelar. {queued} kandidat baru muncul.")
    except Exception as e:
        progress.fail(str(e))
        log.error("api.action_failed", name=name, error=str(e))


@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)) -> dict:
    async def c(stmt) -> int:
        return int(await session.scalar(stmt) or 0)

    return {
        "sources": await c(select(func.count(Source.id))),
        "sources_active": await c(
            select(func.count(Source.id)).where(Source.status == SourceStatus.active)
        ),
        "raw_items": await c(select(func.count(RawItem.id))),
        "stories": await c(select(func.count(Story.id))),
        "candidates": await c(
            select(func.count(CandidateQueue.id)).where(
                CandidateQueue.status == StoryStatus.queued
            )
        ),
        "scripts": await c(select(func.count(Script.id))),
    }


@router.get("/candidates")
async def candidates(
    priority: str | None = None, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    stmt = (
        select(Story, StoryScore, RawItem.source_url, Source.name, StoryPitch)
        .join(StoryScore, StoryScore.story_id == Story.id)
        .join(CandidateQueue, CandidateQueue.story_id == Story.id)
        .join(RawItem, RawItem.id == Story.raw_item_id)
        .outerjoin(Source, Source.id == RawItem.source_id)
        .outerjoin(StoryPitch, StoryPitch.story_id == Story.id)
        .where(CandidateQueue.status == StoryStatus.queued)
        .order_by(StoryScore.final_score.desc())
        .limit(50)
    )
    if priority:
        stmt = stmt.where(StoryScore.priority == priority)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": st.id,
            "title": st.title,
            "summary": st.summary,
            "topic": st.topic,
            "confidence": _val(st.confidence),
            "estimated_minutes": st.estimated_minutes,
            "final_score": round(sc.final_score, 3),
            "priority": _val(sc.priority),
            "source": src_name,
            "source_url": src_url,
            "viral_score": pitch.viral_score if pitch else None,
            "viral_label": pitch.viral_label if pitch else None,
            "viral_reasons": pitch.reasons if pitch else [],
            "where_from": pitch.where_from if pitch else None,
        }
        for st, sc, src_url, src_name, pitch in rows
    ]


@router.get("/stories/{story_id}")
async def story_detail(story_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="not found")
    score = await session.scalar(select(StoryScore).where(StoryScore.story_id == story_id))
    pack = await session.scalar(select(ResearchPack).where(ResearchPack.story_id == story_id))
    pitch = await session.scalar(select(StoryPitch).where(StoryPitch.story_id == story_id))
    raw = await session.get(RawItem, story.raw_item_id)
    scripts = (
        await session.scalars(
            select(Script).where(Script.story_id == story_id).order_by(Script.version.desc())
        )
    ).all()
    breakdown = None
    if score:
        breakdown = {
            "engagement": score.engagement,
            "freshness": score.freshness,
            "novelty": score.novelty,
            "narrative_depth": score.narrative_depth,
            "horror_fit": score.horror_fit,
            "reliability": score.reliability,
            "audience_match": score.audience_match,
            "final_score": round(score.final_score, 3),
            "priority": _val(score.priority),
        }
    return {
        "id": story.id,
        "title": story.title,
        "summary": story.summary,
        "topic": story.topic,
        "subtopics": story.subtopics,
        "entities": story.entities,
        "timeline": story.timeline,
        "confidence": _val(story.confidence),
        "estimated_minutes": story.estimated_minutes,
        "status": _val(story.status),
        "excerpt": (story.cleaned_text or "")[:4000],
        "source_url": raw.source_url if raw else None,
        "posted_at": raw.posted_at if raw else None,
        "score": breakdown,
        "pitch": (
            {
                "viral_score": pitch.viral_score,
                "viral_label": pitch.viral_label,
                "hook": pitch.hook,
                "reasons": pitch.reasons,
                "where_from": pitch.where_from,
            }
            if pitch
            else None
        ),
        "research_pack": (
            {
                "core_summary": pack.core_summary,
                "timeline": pack.timeline,
                "sources": pack.sources,
                "proven": pack.proven,
                "speculative": pack.speculative,
                "open_loops": pack.open_loops,
                "angle": pack.angle,
                "confidence_notes": pack.confidence_notes,
            }
            if pack
            else None
        ),
        "scripts": [
            {"id": s.id, "version": s.version, "status": _val(s.status), "drive_url": s.drive_url}
            for s in scripts
        ],
    }


class DecisionBody(BaseModel):
    action: str
    web_search: bool = False


@router.post("/stories/{story_id}/decision")
async def decide(
    story_id: int, body: DecisionBody, session: AsyncSession = Depends(get_session)
) -> dict:
    cand = await session.scalar(
        select(CandidateQueue).where(CandidateQueue.story_id == story_id)
    )
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    mapping = {
        "approve": (Decision.approve, StoryStatus.approved),
        "reject": (Decision.reject, StoryStatus.scored),
        "later": (Decision.later, StoryStatus.queued),
        "deep": (Decision.deep_research, StoryStatus.researching),
    }
    if body.action not in mapping:
        raise HTTPException(status_code=400, detail="bad action")
    dec, status = mapping[body.action]
    cand.decision = dec
    cand.status = status
    cand.decided_at = datetime.now(timezone.utc)
    story = await session.get(Story, story_id)
    if story:
        story.status = status
    await session.commit()
    if body.action in ("approve", "deep"):
        asyncio.create_task(_bg_generate(story_id, web_search=body.web_search))
    return {"ok": True, "action": body.action}


class RegenBody(BaseModel):
    note: str | None = None
    web_search: bool = False


@router.post("/stories/{story_id}/regenerate")
async def regenerate(story_id: int, body: RegenBody) -> dict:
    asyncio.create_task(
        _bg_generate(story_id, body.note or "tulis ulang lebih natural", web_search=body.web_search)
    )
    return {"ok": True, "started": True}


@router.get("/stories/{story_id}/scripts")
async def story_scripts(
    story_id: int, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        await session.scalars(
            select(Script).where(Script.story_id == story_id).order_by(Script.version.desc())
        )
    ).all()
    return [
        {
            "id": s.id,
            "version": s.version,
            "status": _val(s.status),
            "draft": s.draft,
            "drive_url": s.drive_url,
            "rewrite_note": s.rewrite_note,
            "estimated_minutes": s.estimated_minutes,
            "voice_persona": s.voice_persona,
        }
        for s in rows
    ]


@router.get("/scripts")
async def all_scripts(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(
                Script.id,
                Script.story_id,
                Script.version,
                Script.status,
                Script.drive_url,
                Script.estimated_minutes,
                Story.title,
            )
            .join(Story, Story.id == Script.story_id)
            .order_by(Script.story_id, Script.version.desc())
        )
    ).all()
    seen: set[int] = set()
    out: list[dict] = []
    for sid, story_id, version, status, drive_url, mins, title in rows:
        if story_id in seen:
            continue
        seen.add(story_id)
        out.append(
            {
                "id": sid,
                "story_id": story_id,
                "version": version,
                "status": _val(status),
                "drive_url": drive_url,
                "estimated_minutes": mins,
                "title": title,
            }
        )
    out.sort(key=lambda x: x["story_id"], reverse=True)
    return out[:50]


@router.get("/sources")
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.scalars(select(Source).order_by(Source.id))).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "type": _val(s.type),
            "status": _val(s.status),
            "base_url": s.base_url,
            "priority": s.priority,
            "consecutive_errors": s.consecutive_errors,
            "last_crawled_at": s.last_crawled_at,
            "parser_config": s.parser_config,
        }
        for s in rows
    ]


class SourceBody(BaseModel):
    name: str
    type: str
    feed_url: str | None = None
    channels: list[str] | None = None


@router.post("/sources")
async def add_source(body: SourceBody, session: AsyncSession = Depends(get_session)) -> dict:
    if body.type == "rss":
        if not body.feed_url:
            raise HTTPException(status_code=400, detail="feed_url wajib buat rss")
        src = Source(
            name=body.name,
            type=SourceType.rss,
            base_url=body.feed_url,
            parser_config={"feed_url": body.feed_url, "fetch_full": True, "max_items": 20},
        )
    elif body.type == "youtube":
        src = Source(
            name=body.name,
            type=SourceType.youtube,
            base_url="youtube://watcher",
            parser_config={
                "channels": body.channels or [],
                "years_ago": 1,
                "max_per_channel": 5,
            },
        )
    else:
        raise HTTPException(status_code=400, detail="type harus rss atau youtube")
    session.add(src)
    await session.commit()
    await session.refresh(src)
    return {"id": src.id}


class SourcePatch(BaseModel):
    status: str | None = None
    parser_config: dict | None = None


@router.patch("/sources/{source_id}")
async def patch_source(
    source_id: int, body: SourcePatch, session: AsyncSession = Depends(get_session)
) -> dict:
    src = await session.get(Source, source_id)
    if src is None:
        raise HTTPException(status_code=404, detail="not found")
    if body.status:
        src.status = SourceStatus(body.status)
    if body.parser_config is not None:
        src.parser_config = body.parser_config
    await session.commit()
    return {"ok": True}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    name = await purge_source(session, source_id)
    return {"ok": True, "deleted": name is not None}


class IngestBody(BaseModel):
    video: str
    target_minutes: int | None = None
    web_search: bool = False


@router.post("/ingest/youtube")
async def ingest(body: IngestBody) -> dict:
    asyncio.create_task(_bg_ingest(body.video, body.target_minutes, web_search=body.web_search))
    return {"ok": True, "msg": "video lagi diproses di background, draft nyusul"}


@router.get("/jobs")
async def jobs() -> list[dict]:
    return progress.snapshot()


@router.delete("/jobs/{job_id}")
async def dismiss_job(job_id: str) -> dict:
    return {"ok": progress.dismiss(job_id)}


@router.get("/system")
async def system() -> dict:
    return scheduler_status()


@router.post("/actions/{name}")
async def action(name: str) -> dict:
    if name not in ("cycle", "crawl", "process", "digest", "rescore"):
        raise HTTPException(status_code=400, detail="aksi ga dikenal")
    asyncio.create_task(_bg_action(name))
    return {"ok": True, "started": name}


async def _channel_stats(client: httpx.AsyncClient, channel: str, key: str) -> dict | None:
    params = {"part": "statistics,snippet", "key": key}
    if channel.startswith("UC"):
        params["id"] = channel
    else:
        params["forHandle"] = channel.lstrip("@").split("/")[-1]
    r = await client.get("https://www.googleapis.com/youtube/v3/channels", params=params)
    items = r.json().get("items", [])
    if not items:
        return None
    it = items[0]
    st = it.get("statistics", {})
    sn = it.get("snippet", {})
    return {
        "channel": channel,
        "title": sn.get("title"),
        "thumbnail": sn.get("thumbnails", {}).get("default", {}).get("url"),
        "subscribers": int(st.get("subscriberCount", 0)),
        "views": int(st.get("viewCount", 0)),
        "videos": int(st.get("videoCount", 0)),
    }


@router.get("/youtube/stats")
async def youtube_stats(session: AsyncSession = Depends(get_session)) -> list[dict]:
    key = get_settings().youtube_api_key
    if not key:
        return []
    srcs = (
        await session.scalars(select(Source).where(Source.type == SourceType.youtube))
    ).all()
    channels: list[str] = []
    for s in srcs:
        channels.extend((s.parser_config or {}).get("channels", []))
    out: list[dict] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=20) as client:
        for ch in channels:
            if ch in seen:
                continue
            seen.add(ch)
            try:
                data = await _channel_stats(client, ch, key)
            except Exception as e:
                log.warning("api.yt_stats_failed", channel=ch, error=str(e))
                data = None
            if data:
                out.append(data)
    return out
