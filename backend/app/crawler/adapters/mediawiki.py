from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import quote

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
        categories = self.config.get("categories") or []
        max_total = int(self.config.get("max_total", 0))
        check_robots = not self.config.get("ignore_robots", False)

        pages = await self._collect_pages(api, sep, namespace, limit, categories, check_robots)
        if max_total > 0:
            pages = pages[:max_total]

        import trafilatura

        for pageid, title in pages:
            parse_url = (
                api + sep + f"action=parse&format=json&pageid={pageid}&prop=text&disabletoc=1"
            )
            try:
                pd = await self.rm.get_json(parse_url, check_robots=check_robots)
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

    async def _collect_pages(
        self,
        api: str,
        sep: str,
        namespace: int,
        limit: int,
        categories: list,
        check_robots: bool,
    ) -> list[tuple[int, str | None]]:
        pages: list[tuple[int, str | None]] = []
        if not categories:
            listing = (
                api + sep
                + f"action=query&format=json&list=random&rnnamespace={namespace}&rnlimit={limit}"
            )
            data = await self.rm.get_json(listing, check_robots=check_robots)
            for r in data.get("query", {}).get("random", []):
                if r.get("id") is not None:
                    pages.append((r["id"], r.get("title")))
            return pages

        seen: set[int] = set()
        for cat in categories:
            ct = str(cat)
            if not ct.lower().startswith(("kategori:", "category:")):
                ct = f"Kategori:{ct}"
            listing = (
                api + sep + "action=query&format=json&list=categorymembers"
                + f"&cmtitle={quote(ct)}&cmnamespace={namespace}&cmlimit={limit}&cmtype=page"
            )
            try:
                data = await self.rm.get_json(listing, check_robots=check_robots)
            except Exception as e:
                log.warning("mediawiki.category_failed", category=ct, error=str(e))
                continue
            for m in data.get("query", {}).get("categorymembers", []):
                pid = m.get("pageid")
                if pid is None or pid in seen:
                    continue
                seen.add(pid)
                pages.append((pid, m.get("title")))
        return pages
