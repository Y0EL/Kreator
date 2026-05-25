from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from datetime import datetime
from email.utils import parsedate_to_datetime

from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)

_ATOM = "{http://www.w3.org/2005/Atom}"


class RssAdapter(SourceAdapter):
    type_name = "rss"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        feed_url = self.config.get("feed_url")
        if not feed_url:
            raise ValueError("RssAdapter butuh parser_config.feed_url")
        fetch_full = bool(self.config.get("fetch_full", False))
        max_items = int(self.config.get("max_items", 30))

        resp = await self.rm.get(feed_url)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)

        items = root.findall(".//item")
        if items:
            for item in items[:max_items]:
                async for r in self._from_rss_item(item, fetch_full):
                    yield r
        else:
            for entry in root.findall(f"{_ATOM}entry")[:max_items]:
                async for r in self._from_atom_entry(entry, fetch_full):
                    yield r

    async def _from_rss_item(
        self, item: ET.Element, fetch_full: bool
    ) -> AsyncIterator[RawItemData]:
        link = _text(item, "link")
        title = _text(item, "title")
        desc = _text(item, "description") or ""
        pub = _text(item, "pubDate")
        text = await self._resolve_text(link, desc, fetch_full)
        if link and text:
            yield RawItemData(
                source_url=link, title=title, raw_text=text, posted_at=_parse_date(pub)
            )

    async def _from_atom_entry(
        self, entry: ET.Element, fetch_full: bool
    ) -> AsyncIterator[RawItemData]:
        link_el = entry.find(f"{_ATOM}link")
        link = link_el.get("href") if link_el is not None else None
        title = _text(entry, f"{_ATOM}title")
        content = _text(entry, f"{_ATOM}content") or _text(entry, f"{_ATOM}summary") or ""
        pub = _text(entry, f"{_ATOM}updated") or _text(entry, f"{_ATOM}published")
        text = await self._resolve_text(link, content, fetch_full)
        if link and text:
            yield RawItemData(
                source_url=link, title=title, raw_text=text, posted_at=_parse_date(pub)
            )

    async def _resolve_text(self, link: str | None, fallback: str, fetch_full: bool) -> str:
        if fetch_full and link:
            try:
                import trafilatura

                page = await self.rm.get(link)
                extracted = trafilatura.extract(page.text, include_comments=False)
                if extracted:
                    return extracted
            except Exception as e:
                log.warning("rss.fetch_full_failed", link=link, error=str(e))
        return _strip_tags(fallback)


def _text(el: ET.Element, tag: str) -> str | None:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip()
