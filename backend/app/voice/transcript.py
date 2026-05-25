from __future__ import annotations

import re
from pathlib import Path

_TS_LINE = re.compile(r"\[\d{1,2}:\d{2}\]\((?:https?://)?\S+?\)(?:\((?:https?://)?\S+?\))*\s*")
_STAGE = re.compile(r"\[(?:Musik|Music|Tepuk tangan|Applause|Tertawa|Suara)\]", re.IGNORECASE)
_WS = re.compile(r"\s+")


def clean_transcript(raw: str) -> str:
    text = _TS_LINE.sub(" ", raw)
    text = _STAGE.sub(" ", text)
    text = _WS.sub(" ", text)
    return text.strip()


def persona_from_filename(path: str | Path) -> str:
    name = Path(path).stem.lower()
    return name.split("-", 1)[0] if "-" in name else name


def chunk_text(text: str, chunk_chars: int = 1500, overlap: int = 150) -> list[str]:
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + chunk_chars, n)
        chunks.append(text[i:end].strip())
        if end >= n:
            break
        i = end - overlap
    return [c for c in chunks if len(c) > 200]


def load_corpus(lesson_dir: str | Path) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for fp in sorted(Path(lesson_dir).glob("*.txt")):
        persona = persona_from_filename(fp)
        cleaned = clean_transcript(fp.read_text(encoding="utf-8", errors="ignore"))
        out.setdefault(persona, []).append((fp.name, cleaned))
    return out
