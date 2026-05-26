from __future__ import annotations

import html

from app.logging import get_logger

log = get_logger(__name__)


def _title(t: object) -> str | None:
    return html.unescape(t) if isinstance(t, str) else None


def _flat(url: str, limit: int) -> list[dict]:
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "playlistend": limit,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return (info or {}).get("entries") or []


def _thumb(entry: dict, fallback: str | None) -> str | None:
    th = entry.get("thumbnails") or []
    if th:
        return th[-1].get("url") or fallback
    return entry.get("thumbnail") or fallback


def list_channel_videos(channel_id: str, limit: int = 20) -> list[dict]:
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    out: list[dict] = []
    try:
        entries = _flat(url, limit)
    except Exception as e:
        log.warning("ytscrape.videos_failed", channel=channel_id, error=str(e))
        return []
    for e in entries:
        vid = e.get("id")
        if not vid:
            continue
        out.append({
            "video_id": vid,
            "title": _title(e.get("title")),
            "thumbnail": _thumb(e, f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"),
            "views": int(e.get("view_count") or 0),
            "published_at": None,
        })
    return out


def list_channel_playlists(channel_id: str, limit: int = 20) -> list[dict]:
    url = f"https://www.youtube.com/channel/{channel_id}/playlists"
    out: list[dict] = []
    try:
        entries = _flat(url, limit)
    except Exception as e:
        log.warning("ytscrape.playlists_failed", channel=channel_id, error=str(e))
        return []
    for e in entries:
        pid = e.get("id")
        if not pid:
            continue
        out.append({
            "playlist_id": pid,
            "title": _title(e.get("title")),
            "thumbnail": _thumb(e, None),
            "count": int(e.get("playlist_count") or e.get("video_count") or 0),
        })
    return out
