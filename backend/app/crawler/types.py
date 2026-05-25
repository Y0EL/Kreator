from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class RawItemData:
    source_url: str
    raw_text: str
    title: str | None = None
    author_name: str | None = None
    posted_at: datetime | None = None
    raw_html: str | None = None
    reply_count: int | None = None
    view_count: int | None = None
    media_links: list[str] = field(default_factory=list)
