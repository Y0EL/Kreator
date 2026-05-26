from __future__ import annotations

import time
from threading import Lock
from typing import Any

_store: dict[str, tuple[Any, float]] = {}
_lock = Lock()


def get(key: str) -> Any | None:
    with _lock:
        hit = _store.get(key)
        if hit is None:
            return None
        val, exp = hit
        if time.time() > exp:
            _store.pop(key, None)
            return None
        return val


def set(key: str, value: Any, ttl: float) -> None:
    with _lock:
        _store[key] = (value, time.time() + ttl)


def invalidate(prefix: str) -> None:
    with _lock:
        for k in [k for k in _store if k.startswith(prefix)]:
            _store.pop(k, None)
