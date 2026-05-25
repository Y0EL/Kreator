from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import quote

from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)


class OpenSerpAdapter(SourceAdapter):
    type_name = "search"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        query = self.config.get("query")
        if not query:
            raise ValueError("OpenSerpAdapter butuh parser_config.query")
        base = self.config.get("openserp_url", "http://127.0.0.1:7000")
        engine = self.config.get("engine", "google")
        lang = self.config.get("lang", "ID")
        limit = int(self.config.get("limit", 10))
        min_chars = int(self.config.get("min_chars", 800))
        url = f"{base}/{engine}/search?lang={lang}&limit={limit}&text={quote(query)}"

        results = await self.rm.get_json(url)
        if isinstance(results, dict):
            results = results.get("results", [])

        import trafilatura

        for item in results:
            link = item.get("url")
            if not link:
                continue
            try:
                page = await self.rm.get(link)
            except Exception as e:
                log.warning("openserp.fetch_failed", link=link, error=str(e))
                continue
            text = trafilatura.extract(page.text, include_comments=False) or ""
            if len(text) < min_chars:
                continue
            yield RawItemData(source_url=link, title=item.get("title"), raw_text=text)
