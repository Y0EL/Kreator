from __future__ import annotations

from app.crawler.types import RawItemData

MIN_TEXT_CHARS = 300


def validate(item: RawItemData) -> tuple[bool, str | None]:
    if not item.source_url or not item.source_url.startswith("http"):
        return False, "source_url tidak valid"
    text = (item.raw_text or "").strip()
    if len(text) < MIN_TEXT_CHARS:
        return False, f"raw_text terlalu pendek (<{MIN_TEXT_CHARS})"
    return True, None
