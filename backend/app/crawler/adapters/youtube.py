from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.config import get_settings
from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)


_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")


def extract_video_id(value: str) -> str | None:
    m = _VIDEO_ID.search(value or "")
    if m:
        return m.group(1)
    stripped = (value or "").strip()
    return stripped if re.fullmatch(r"[A-Za-z0-9_-]{11}", stripped) else None


def _window(years_ago: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    year = now.year - years_ago
    month = now.month
    after = datetime(year, month, 1, tzinfo=timezone.utc)
    before = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return after.strftime(fmt), before.strftime(fmt)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fetch_caption(video_id: str, proxy: str | None) -> str:
    key = get_settings().supadata_api_key
    if key:
        return _fetch_supadata(video_id, key)

    from youtube_transcript_api import YouTubeTranscriptApi

    proxies = {"http": proxy, "https": proxy} if proxy else None
    segments = YouTubeTranscriptApi.get_transcript(
        video_id, languages=["id", "en"], proxies=proxies
    )
    return " ".join(seg["text"] for seg in segments).strip()


def _supadata_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            str(c.get("text", "")) for c in content if isinstance(c, dict)
        ).strip()
    return ""


def _fetch_supadata(video_id: str, key: str) -> str:
    import time

    import httpx

    headers = {"x-api-key": key}
    params = {"url": f"https://www.youtube.com/watch?v={video_id}", "text": "true", "lang": "id"}
    with httpx.Client(timeout=60) as c:
        r = c.get("https://api.supadata.ai/v1/transcript", params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        text = _supadata_text(data.get("content"))
        if text:
            return text
        job_id = data.get("jobId") or data.get("id")
        if not job_id:
            return ""
        for _ in range(20):
            time.sleep(3)
            jr = c.get(f"https://api.supadata.ai/v1/transcript/{job_id}", headers=headers)
            jr.raise_for_status()
            jd = jr.json()
            status = jd.get("status")
            if status in ("completed", "succeeded", "done"):
                return _supadata_text(jd.get("content") or jd.get("transcript"))
            if status in ("failed", "error"):
                return ""
    return ""


class YouTubeAdapter(SourceAdapter):
    type_name = "youtube"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        settings = get_settings()
        api_key = settings.youtube_api_key
        if not api_key:
            raise ValueError("YouTubeAdapter butuh YOUTUBE_API_KEY")
        channels = self.config.get("channels") or []
        if not channels:
            raise ValueError("YouTubeAdapter butuh parser_config.channels")
        years_ago = int(self.config.get("years_ago", 1))
        per_channel = int(self.config.get("max_per_channel", 5))
        min_chars = int(self.config.get("min_chars", 1500))
        after, before = _window(years_ago)

        for channel in channels:
            channel_id = await self._resolve_channel(channel, api_key)
            if not channel_id:
                continue
            url = (
                "https://www.googleapis.com/youtube/v3/search?part=snippet"
                f"&channelId={channel_id}&type=video&order=viewCount"
                f"&maxResults={per_channel}&publishedAfter={after}"
                f"&publishedBefore={before}&key={api_key}"
            )
            data = await self.rm.get_json(url)
            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                snippet = item.get("snippet", {})
                text = await self._transcript(video_id)
                if not text or len(text) < min_chars:
                    continue
                yield RawItemData(
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    title=snippet.get("title"),
                    author_name=snippet.get("channelTitle"),
                    posted_at=_parse_dt(snippet.get("publishedAt")),
                    raw_text=text,
                )

    async def _resolve_channel(self, channel: str, api_key: str) -> str | None:
        if channel.startswith("UC"):
            return channel
        handle = channel.lstrip("@").split("/")[-1]
        url = (
            "https://www.googleapis.com/youtube/v3/channels?part=id"
            f"&forHandle={handle}&key={api_key}"
        )
        try:
            data = await self.rm.get_json(url)
            items = data.get("items", [])
            return items[0]["id"] if items else None
        except Exception as e:
            log.warning("youtube.resolve_failed", channel=channel, error=str(e))
            return None

    async def _transcript(self, video_id: str) -> str | None:
        proxy = get_settings().crawl_proxy_url or None
        try:
            return await asyncio.to_thread(_fetch_caption, video_id, proxy)
        except Exception as e:
            log.warning("youtube.caption_failed", video_id=video_id, error=str(e))
            return None
