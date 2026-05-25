from __future__ import annotations

import re

from app.config import get_settings
from app.integrations import r2
from app.logging import get_logger

log = get_logger(__name__)


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "untitled"


def save_doc(title: str, content: str) -> str:
    key = f"docs/{_slug(title)}.md"
    r2.put_text(key, f"# {title}\n\n{content}", "text/markdown; charset=utf-8")
    settings = get_settings()
    if settings.r2_public_url:
        url = settings.r2_public_url.rstrip("/") + "/" + key
    else:
        url = f"r2://{settings.r2_bucket}/{key}"
    log.info("doc.saved", title=title, url=url)
    return url
