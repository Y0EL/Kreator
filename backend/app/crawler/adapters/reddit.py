from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)


class RedditAdapter(SourceAdapter):
    type_name = "reddit"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        sub = self.config.get("subreddit")
        if not sub:
            raise ValueError("RedditAdapter butuh parser_config.subreddit")
        listing = self.config.get("listing", "top")
        limit = int(self.config.get("limit", 25))
        min_chars = int(self.config.get("min_chars", 800))
        url = f"https://www.reddit.com/r/{sub}/{listing}.json?limit={limit}"
        if listing == "top":
            url += f"&t={self.config.get('timeframe', 'month')}"

        data = await self.rm.get_json(url)
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            selftext = (post.get("selftext") or "").strip()
            if len(selftext) < min_chars:
                continue
            permalink = post.get("permalink", "")
            yield RawItemData(
                source_url=f"https://www.reddit.com{permalink}",
                title=post.get("title"),
                author_name=post.get("author"),
                posted_at=_ts(post.get("created_utc")),
                raw_text=selftext,
                reply_count=post.get("num_comments"),
                view_count=post.get("ups"),
                media_links=_media(post),
            )


def _ts(created_utc: float | None) -> datetime | None:
    if not created_utc:
        return None
    return datetime.fromtimestamp(created_utc, tz=timezone.utc)


def _media(post: dict) -> list[str]:
    links: list[str] = []
    url = post.get("url_overridden_by_dest") or post.get("url")
    if url and any(url.lower().endswith(ext) for ext in (".jpg", ".png", ".gif", ".mp4")):
        links.append(url)
    return links
