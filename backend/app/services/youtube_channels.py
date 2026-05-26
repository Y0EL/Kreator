from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import SourceType
from app.db.models import ChannelStat, Source
from app.logging import get_logger
from app.services.sources import purge_source

log = get_logger(__name__)

_YT = "https://www.googleapis.com/youtube/v3"


async def resolve_channel_id(channel: str, key: str) -> str | None:
    ch = channel.strip()
    if ch.startswith("UC") and len(ch) >= 20:
        return ch
    handle = ch.lstrip("@").split("/")[-1]
    async with httpx.AsyncClient(timeout=20) as c:
        try:
            r = await c.get(
                f"{_YT}/channels", params={"part": "id", "forHandle": handle, "key": key}
            )
            items = r.json().get("items", [])
            if items:
                return items[0]["id"]
        except Exception as e:
            log.warning("yt.resolve_handle_failed", channel=channel, error=str(e))
        try:
            r = await c.get(
                f"{_YT}/search",
                params={"part": "snippet", "type": "channel", "q": ch.lstrip("@"),
                        "maxResults": 1, "key": key},
            )
            items = r.json().get("items", [])
            if items:
                return items[0]["id"]["channelId"]
        except Exception as e:
            log.warning("yt.resolve_search_failed", channel=channel, error=str(e))
    return None


async def canonical_youtube_source(
    session: AsyncSession, create: bool = True
) -> Source | None:
    srcs = list(
        (
            await session.scalars(
                select(Source).where(Source.type == SourceType.youtube).order_by(Source.id)
            )
        ).all()
    )
    if not srcs:
        if not create:
            return None
        src = Source(
            name="YouTube",
            type=SourceType.youtube,
            base_url="youtube://watcher",
            parser_config={"channels": [], "max_per_channel": 10},
        )
        session.add(src)
        await session.commit()
        await session.refresh(src)
        return src

    primary = srcs[0]
    chans = list((primary.parser_config or {}).get("channels") or [])
    for extra in srcs[1:]:
        for ch in (extra.parser_config or {}).get("channels") or []:
            if ch not in chans:
                chans.append(ch)
        await purge_source(session, extra.id)
    cfg = dict(primary.parser_config or {})
    cfg["channels"] = chans
    cfg.setdefault("max_per_channel", 10)
    primary.parser_config = cfg
    if primary.name in ("yt", "YouTube Watcher"):
        primary.name = "YouTube"
    await session.commit()
    return primary


async def add_channel(session: AsyncSession, channel: str) -> dict:
    key = get_settings().youtube_api_key
    cid = await resolve_channel_id(channel, key) if key else None
    src = await canonical_youtube_source(session, create=True)
    assert src is not None
    cfg = dict(src.parser_config or {})
    chans = list(cfg.get("channels") or [])
    val = cid or channel.strip()
    added = val not in chans
    if added:
        chans.append(val)
        cfg["channels"] = chans
        src.parser_config = cfg
        await session.commit()
    return {"added": added, "channel": val, "total": len(chans)}


async def remove_channel(session: AsyncSession, channel: str) -> dict:
    src = await canonical_youtube_source(session, create=False)
    if src is None:
        return {"removed": False, "total": 0}
    cfg = dict(src.parser_config or {})
    chans = list(cfg.get("channels") or [])
    new = [c for c in chans if c != channel]
    cfg["channels"] = new
    src.parser_config = cfg
    await session.commit()
    return {"removed": len(new) != len(chans), "total": len(new)}


def monitored_channels(src: Source | None) -> list[str]:
    if src is None:
        return []
    return list((src.parser_config or {}).get("channels") or [])


async def snapshot_channel_stats(session: AsyncSession) -> int:
    s = get_settings()
    key = s.youtube_api_key
    if not key:
        return 0
    refs: list[str] = []
    owner_id = await resolve_channel_id(s.owner_yt_handle, key)
    if owner_id:
        refs.append(owner_id)
    src = await canonical_youtube_source(session, create=False)
    for ch in monitored_channels(src):
        cid = ch if (ch.startswith("UC") and len(ch) >= 20) else await resolve_channel_id(ch, key)
        if cid and cid not in refs:
            refs.append(cid)
    if not refs:
        return 0
    today = datetime.now(timezone.utc).date()
    written = 0
    async with httpx.AsyncClient(timeout=20) as c:
        for i in range(0, len(refs), 50):
            batch = refs[i : i + 50]
            r = await c.get(
                f"{_YT}/channels",
                params={"part": "statistics", "id": ",".join(batch), "key": key},
            )
            for it in r.json().get("items", []):
                cid = it.get("id")
                st = it.get("statistics", {})
                if not cid:
                    continue
                row = await session.scalar(
                    select(ChannelStat).where(
                        ChannelStat.channel_id == cid, ChannelStat.date == today
                    )
                )
                subs = int(st.get("subscriberCount", 0))
                views = int(st.get("viewCount", 0))
                vids = int(st.get("videoCount", 0))
                if row:
                    row.subscribers, row.views, row.videos = subs, views, vids
                else:
                    session.add(
                        ChannelStat(
                            channel_id=cid, date=today,
                            subscribers=subs, views=views, videos=vids,
                        )
                    )
                    written += 1
    await session.commit()
    log.info("yt.stats_snapshot", channels=len(refs), new_rows=written)
    return written
