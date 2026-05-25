from __future__ import annotations

import re

_QUOTE_LINE = re.compile(r"^\s*>.*$", re.MULTILINE)
_SIG = re.compile(r"^\s*[-—]{2,}\s*$.*", re.MULTILINE | re.DOTALL)
_MULTI_NL = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_ZERO_WIDTH = re.compile(r"[​-‏﻿]")
_EMOJI_RUN = re.compile(r"([\U0001F000-\U0001FAFF☀-➿]){3,}")
_URL = re.compile(r"http\S+")

_ID = {"yang", "dan", "di", "ini", "itu", "dengan", "tidak", "saya", "aku", "dia", "kita"}
_EN = {"the", "and", "is", "was", "with", "that", "this", "you", "have", "are", "not"}


def clean_text(raw: str) -> str:
    text = _ZERO_WIDTH.sub("", raw)
    text = _QUOTE_LINE.sub("", text)
    text = _SIG.sub("", text)
    text = _EMOJI_RUN.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()


def detect_language(text: str) -> str | None:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())[:400]
    if not tokens:
        return None
    id_hits = sum(t in _ID for t in tokens)
    en_hits = sum(t in _EN for t in tokens)
    if id_hits == en_hits == 0:
        return None
    return "id" if id_hits >= en_hits else "en"


def strip_urls(text: str) -> str:
    return _URL.sub("", text)
