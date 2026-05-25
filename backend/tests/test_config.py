from __future__ import annotations

from datetime import time

from app.config import Settings


def test_collection_window_same_day():
    s = Settings(collection_window_start="10:00", collection_window_end="22:00")
    assert s.in_window(s.collection_window, time(14, 0)) is True
    assert s.in_window(s.collection_window, time(23, 0)) is False


def test_approval_window_crosses_midnight():
    s = Settings(approval_window_start="01:00", approval_window_end="10:00")
    assert s.in_window(s.approval_window, time(3, 0)) is True
    assert s.in_window(s.approval_window, time(11, 0)) is False


def test_cors_origins_split():
    s = Settings(cors_allow_origins="http://a.com, http://b.com")
    assert s.cors_origins == ["http://a.com", "http://b.com"]
