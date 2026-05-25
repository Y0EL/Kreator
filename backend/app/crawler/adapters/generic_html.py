from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)


class GenericHtmlAdapter(SourceAdapter):
    type_name = "generic_html"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        list_url = self.config.get("list_url") or self.source.base_url
        if not list_url:
            raise ValueError("GenericHtmlAdapter butuh parser_config.list_url atau base_url")
        selector = self.config.get("item_link_selector", "a")
        link_contains = self.config.get("link_contains")
        max_items = int(self.config.get("max_items", 20))

        listing = await self.rm.get(list_url)
        tree = HTMLParser(listing.text)
        seen: set[str] = set()
        links: list[str] = []
        for node in tree.css(selector):
            href = node.attributes.get("href")
            if not href:
                continue
            full = urljoin(list_url, href)
            if link_contains and link_contains not in full:
                continue
            if full in seen:
                continue
            seen.add(full)
            links.append(full)
            if len(links) >= max_items:
                break

        import trafilatura

        for link in links:
            try:
                page = await self.rm.get(link)
            except Exception as e:
                log.warning("generic.fetch_failed", link=link, error=str(e))
                continue
            extracted = trafilatura.extract(
                page.text, include_comments=False, include_tables=False
            )
            if not extracted:
                continue
            title = None
            t = HTMLParser(page.text).css_first("title")
            if t is not None:
                title = t.text(strip=True)
            yield RawItemData(source_url=link, title=title, raw_text=extracted, raw_html=page.text)
