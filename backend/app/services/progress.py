from __future__ import annotations

import contextvars
import time
import uuid
from threading import Lock

_jobs: dict[str, dict] = {}
_lock = Lock()
_current: contextvars.ContextVar[str | None] = contextvars.ContextVar("progress_job", default=None)


def start(kind: str, title: str | None = None) -> str:
    jid = uuid.uuid4().hex[:12]
    now = time.time()
    with _lock:
        _jobs[jid] = {
            "id": jid,
            "kind": kind,
            "title": title,
            "stage": "Mengantri",
            "percent": 3,
            "status": "running",
            "error": None,
            "story_id": None,
            "created_at": now,
            "updated_at": now,
        }
    _current.set(jid)
    return jid


def step(stage: str, percent: int, *, story_id: int | None = None, title: str | None = None) -> None:
    jid = _current.get()
    if not jid:
        return
    with _lock:
        j = _jobs.get(jid)
        if not j:
            return
        j["stage"] = stage
        j["percent"] = max(int(j["percent"]), int(percent))
        if story_id is not None:
            j["story_id"] = story_id
        if title:
            j["title"] = title
        j["updated_at"] = time.time()


def fail(error: str) -> None:
    jid = _current.get()
    if not jid:
        return
    with _lock:
        j = _jobs.get(jid)
        if j:
            j["status"] = "error"
            j["stage"] = "Gagal"
            j["error"] = str(error)[:300]
            j["updated_at"] = time.time()


def done(title: str | None = None) -> None:
    jid = _current.get()
    if not jid:
        return
    with _lock:
        j = _jobs.get(jid)
        if j:
            j["status"] = "done"
            j["stage"] = "Selesai"
            j["percent"] = 100
            if title:
                j["title"] = title
            j["updated_at"] = time.time()


def snapshot() -> list[dict]:
    now = time.time()
    with _lock:
        for k in list(_jobs):
            j = _jobs[k]
            if j["status"] != "running" and now - j["updated_at"] > 900:
                del _jobs[k]
        return sorted(_jobs.values(), key=lambda x: x["created_at"], reverse=True)
