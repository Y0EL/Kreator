from __future__ import annotations

import re

_HYPHEN_CODEPOINTS = [0x2010, 0x2011]
_PUNCT_DASH_CODEPOINTS = [0x2012, 0x2013, 0x2014, 0x2015, 0x2212, 0x2E3A, 0x2E3B]
_DASH_CODEPOINTS = _HYPHEN_CODEPOINTS + _PUNCT_DASH_CODEPOINTS

_TRANSLATE = (
    {cp: "-" for cp in _HYPHEN_CODEPOINTS}
    | {cp: "," for cp in _PUNCT_DASH_CODEPOINTS}
    | {
        0x201C: '"',
        0x201D: '"',
        0x201E: '"',
        0x201F: '"',
        0x2018: "'",
        0x2019: "'",
        0x201A: "'",
        0x201B: "'",
        0x2026: "...",
        0x00A0: " ",
    }
)

_MULTI_COMMA = re.compile(r"(?:\s*,\s*){2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.])")
_COMMA_THEN_PERIOD = re.compile(r",\s*\.")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NL = re.compile(r"\n{3,}")


def sanitize_script(text: str) -> str:
    text = text.translate(_TRANSLATE)
    text = text.replace(";", ".")
    text = _MULTI_COMMA.sub(", ", text)
    text = _COMMA_THEN_PERIOD.sub(".", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()


def has_forbidden_typography(text: str) -> bool:
    if ";" in text:
        return True
    return any(chr(cp) in text for cp in _DASH_CODEPOINTS)
