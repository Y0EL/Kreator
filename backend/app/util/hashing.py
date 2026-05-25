from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def normalize_for_hash(text: str) -> str:
    return _WS.sub(" ", text.strip().lower())


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_for_hash(text).encode("utf-8")).hexdigest()
