from __future__ import annotations

from collections.abc import AsyncIterator

from app.crawler.base import SourceAdapter
from app.crawler.types import RawItemData
from app.logging import get_logger

log = get_logger(__name__)


class MediaWikiAdapter(SourceAdapter):
    type_name = "mediawiki"

    async def crawl(self) -> AsyncIterator[RawItemData]:
        api = self.config.get("api_url")
        if not api:
            raise ValueError("MediaWikiAdapter butuh parser_config.api_url")
        limit = int(self.config.get("limit", 15))
        min_chars = int(self.config.get("min_chars", 1500))
        namespace = int(self.config.get("namespace", 0))
        base = self.config.get("page_base") or api.replace("/api.php", "/wiki/")
        sep = "&" if "?" in api else "?"

        listing = (
            api + sep
            + f"action=query&format=json&list=random&rnnamespace={namespace}&rnlimit={limit}"
        )
        data = await self.rm.get_json(listing)
        randoms = data.get("query", {}).get("random", [])

        import trafilatura

        for r in randoms:
            pageid = r.get("id")
            title = r.get("title")
            if pageid is None:
                continue
            parse_url = (
                api + sep + f"action=parse&format=json&pageid={pageid}&prop=text&disabletoc=1"
            )
            try:
                pd = await self.rm.get_json(parse_url)
            except Exception as e:
                log.warning("mediawiki.parse_failed", pageid=pageid, error=str(e))
                continue
            html = pd.get("parse", {}).get("text", {}).get("*", "")
            if not html:
                continue
            text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
            if len(text) < min_chars:
                continue
            yield RawItemData(
                source_url=base + (title or "").replace(" ", "_"),
                title=title,
                raw_text=text,
            )
