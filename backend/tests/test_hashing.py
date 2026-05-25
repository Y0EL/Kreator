from __future__ import annotations

from app.util.hashing import content_hash, normalize_for_hash


def test_normalize_collapses_whitespace_and_case():
    assert normalize_for_hash("  Hello   World \n") == "hello world"


def test_same_content_same_hash():
    a = content_hash("Cerita horor di desa.")
    b = content_hash("cerita   horor di desa.")
    assert a == b


def test_different_content_different_hash():
    assert content_hash("satu") != content_hash("dua")
