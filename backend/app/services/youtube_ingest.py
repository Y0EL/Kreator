from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.agents.delivery import generate_and_deliver
from app.config import get_settings
from app.crawler.adapters.youtube import _fetch_caption, _fetch_whisper, extract_video_id
from app.db.enums import SourceType
from app.db.models import RawItem, Source, Story
from app.db.session import SessionLocal
from app.integrations import r2
from app.logging import get_logger
from app.pipeline.processor import process_raw_item
from app.services import progress
from app.util.hashing import content_hash

log = get_logger(__name__)


async def ingest_youtube(
    video: str, target_minutes: int | None = None, web_search: bool = False
) -> str:
    s = get_settings()
    if not s.youtube_api_key:
        return "YOUTUBE_API_KEY belum di-set."

    progress.step("Mencari video", 8)
    vid = extract_video_id(video)
    title: str | None = None
    async with httpx.AsyncClient(timeout=25) as c:
        if not vid:
            r = await c.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": video, "type": "video",
                        "maxResults": 1, "key": s.youtube_api_key},
            )
            items = r.json().get("items", [])
            for it in items:
                cand = it.get("id")
                if isinstance(cand, dict) and cand.get("videoId"):
                    vid = cand["videoId"]
                    title = it.get("snippet", {}).get("title")
                    break
            if not vid:
                progress.fail(f"Video ga ketemu buat: {video}")
                return f"Video ga ketemu buat: {video}"
        else:
            r = await c.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet", "id": vid, "key": s.youtube_api_key},
            )
            items = r.json().get("items", [])
            title = items[0]["snippet"]["title"] if items else f"YouTube {vid}"

    progress.step("Mengambil transkrip", 22, title=title)
    proxy = s.crawl_proxy_url or None
    try:
        text = await asyncio.to_thread(_fetch_caption, vid, proxy)
    except Exception:
        progress.step("Transkrip audio (Whisper)", 30, title=title)
        try:
            text = await asyncio.to_thread(_fetch_whisper, vid)
        except Exception as e:
            progress.fail(f"Gagal transkrip: {e}")
            return f"Gagal ambil transkrip video {vid}: {e}"
    if not text or len(text) < 500:
        progress.fail("Transkrip kosong atau kependek.")
        return "Transkrip kosong atau kependek, ga bisa diproses."

    progress.step("Menyiapkan cerita", 52, title=title)
    url = f"https://www.youtube.com/watch?v={vid}"
    async with SessionLocal() as session:
        src = await session.scalar(select(Source).where(Source.name == "Manual YouTube"))
        if src is None:
            src = Source(
                name="Manual YouTube", type=SourceType.submission, base_url="youtube://manual"
            )
            session.add(src)
            await session.flush()
        h = content_hash(text)
        existing = await session.scalar(select(RawItem).where(RawItem.raw_hash == h))
        if existing is None:
            key = r2.raw_key(src.id, h)
            r2.put_text(key, text)
            item = RawItem(
                source_id=src.id, source_url=url, title=title,
                crawled_at=datetime.now(timezone.utc), r2_key_raw=key, raw_hash=h,
                raw_excerpt=text[:2000],
            )
            session.add(item)
            await session.flush()
            story = await process_raw_item(session, item)
            story_id = story.id if story else None
        else:
            story = await session.scalar(select(Story).where(Story.raw_item_id == existing.id))
            story_id = story.id if story else None
        if target_minutes and story:
            story.estimated_minutes = int(target_minutes)
        await session.commit()

    if not story_id:
        progress.fail("Gagal proses jadi cerita.")
        return "Gagal proses jadi cerita."
    progress.step("Menyiapkan draft", 58, story_id=story_id, title=title)
    return await generate_and_deliver(story_id, web_search=web_search)
