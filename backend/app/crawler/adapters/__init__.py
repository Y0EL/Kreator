from __future__ import annotations

from app.crawler.adapters.generic_html import GenericHtmlAdapter
from app.crawler.adapters.mediawiki import MediaWikiAdapter
from app.crawler.adapters.openserp import OpenSerpAdapter
from app.crawler.adapters.reddit import RedditAdapter
from app.crawler.adapters.rss import RssAdapter
from app.crawler.base import SourceAdapter
from app.crawler.request_manager import RequestManager
from app.db.enums import SourceType
from app.db.models import Source

_REGISTRY: dict[SourceType, type[SourceAdapter]] = {
    SourceType.reddit: RedditAdapter,
    SourceType.rss: RssAdapter,
    SourceType.blog_archive: GenericHtmlAdapter,
    SourceType.forum: GenericHtmlAdapter,
    SourceType.media: GenericHtmlAdapter,
    SourceType.mediawiki: MediaWikiAdapter,
    SourceType.search: OpenSerpAdapter,
}


def get_adapter(source: Source, rm: RequestManager) -> SourceAdapter:
    stype = source.type if isinstance(source.type, SourceType) else SourceType(source.type)
    try:
        cls = _REGISTRY[stype]
    except KeyError as e:
        raise ValueError(f"Tidak ada adapter untuk tipe sumber: {stype}") from e
    return cls(source, rm)
