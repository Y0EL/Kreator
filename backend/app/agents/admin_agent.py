from __future__ import annotations

import asyncio
import json

import httpx
from sqlalchemy import func, select

from app.agents.memory import append_turn, load_history, maybe_compact
from app.config import get_settings
from app.db.enums import SourceStatus, SourceType, StoryStatus
from app.db.models import CandidateQueue, Knowledge, RawItem, Source, Story, StoryScore
from app.db.session import SessionLocal
from app.llm import client
from app.logging import get_logger

log = get_logger(__name__)

ADMIN_SYSTEM = (
    "Lo asisten admin buat sistem crawler konten horor/misteri punya Yoel. Ngobrol SANTAI dan "
    "akrab pakai bahasa sehari-hari (boleh 'gue/lo'), JANGAN formal, JANGAN pakai 'saya/anda'. "
    "Lo bisa pakai tools buat lihat, nambah, ngubah, ngapus sumber dan channel YouTube, lihat "
    "kandidat, statistik, dan ngelola knowledge base. Jawab ringkas. Kalau cuma diajak ngobrol "
    "biasa, balas singkat TANPA manggil tool. Jangan ngarang data, selalu pakai tool buat data "
    "nyata. Konfirmasi singkat abis ngelakuin aksi. "
    "FORMAT jawaban buat Telegram pakai HTML: <b>tebal</b>, <i>miring</i>, <u>garis bawah</u>, "
    "<s>coret</s>, <code>monospace</code>, dan <pre>blok monospace buat daftar/tabel/kotak ala "
    "terminal</pre>. Pakai EMOJI yang relevan biar idup (mis. 📡 sumber, 🟢 active, ⏸️ paused, "
    "🔥 kandidat, 🎬 youtube, 🗑️ hapus). Buat nampilin data/daftar, bungkus dalam <pre> biar rapi. "
    "DILARANG KERAS pakai tanda em dash, en dash, atau titik koma. Pakai tanda hubung biasa atau "
    "koma. Jangan nawarin aksi yang ga diminta."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_sources",
        "description": "Lihat semua sumber crawl beserta status dan tipe.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "ingest_youtube",
        "description": "Ambil SATU video YouTube spesifik (URL atau judul buat dicari), transkrip, "
                       "lalu langsung bikin draft skrip versi sendiri dan kirim ke grup.",
        "parameters": {"type": "object", "properties": {
            "video": {"type": "string", "description": "URL video YouTube atau judul"}},
            "required": ["video"]},
    }},
    {"type": "function", "function": {
        "name": "add_youtube_channel",
        "description": "Tambah channel YouTube untuk dipantau (handle @nama, URL, atau channelId UC...).",
        "parameters": {"type": "object", "properties": {
            "channel": {"type": "string"}}, "required": ["channel"]},
    }},
    {"type": "function", "function": {
        "name": "add_rss_source",
        "description": "Tambah sumber RSS baru.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "feed_url": {"type": "string"}},
            "required": ["name", "feed_url"]},
    }},
    {"type": "function", "function": {
        "name": "set_source_status",
        "description": "Ubah status sumber (active, paused, disabled) by id atau nama.",
        "parameters": {"type": "object", "properties": {
            "identifier": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "paused", "disabled"]}},
            "required": ["identifier", "status"]},
    }},
    {"type": "function", "function": {
        "name": "delete_source",
        "description": "Hapus sumber permanen by id atau nama.",
        "parameters": {"type": "object", "properties": {
            "identifier": {"type": "string"}}, "required": ["identifier"]},
    }},
    {"type": "function", "function": {
        "name": "list_candidates",
        "description": "Lihat kandidat cerita teratas di antrian.",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer"}}},
    }},
    {"type": "function", "function": {
        "name": "stats",
        "description": "Statistik ringkas: jumlah sumber, raw item, story, kandidat.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "add_knowledge",
        "description": "Simpan catatan knowledge (preferensi/aturan/konteks) agar sistem makin pintar.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "content": {"type": "string"}},
            "required": ["title", "content"]},
    }},
    {"type": "function", "function": {
        "name": "search_knowledge",
        "description": "Cari catatan knowledge yang relevan.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]},
    }},
]


async def _find_source(session, identifier: str) -> Source | None:
    ident = str(identifier).strip()
    if ident.isdigit():
        return await session.get(Source, int(ident))
    return await session.scalar(select(Source).where(Source.name.ilike(f"%{ident}%")))


async def _ingest_youtube(video: str) -> str:
    from datetime import datetime, timezone

    from app.agents.delivery import generate_and_deliver
    from app.crawler.adapters.youtube import _fetch_caption, _fetch_whisper, extract_video_id
    from app.integrations import r2
    from app.pipeline.processor import process_raw_item
    from app.util.hashing import content_hash

    s = get_settings()
    if not s.youtube_api_key:
        return "YOUTUBE_API_KEY belum di-set."

    vid = extract_video_id(video)
    title: str | None = None
    async with httpx.AsyncClient(timeout=25) as c:
        if not vid:
            r = await c.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": video, "type": "video",
                        "maxResults": 1, "key": s.youtube_api_key},
            )
            items = r.json().get("items", [])
            if not items:
                return f"Video ga ketemu buat: {video}"
            vid = items[0]["id"]["videoId"]
            title = items[0]["snippet"]["title"]
        else:
            r = await c.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet", "id": vid, "key": s.youtube_api_key},
            )
            items = r.json().get("items", [])
            title = items[0]["snippet"]["title"] if items else f"YouTube {vid}"

    proxy = s.crawl_proxy_url or None
    try:
        text = await asyncio.to_thread(_fetch_caption, vid, proxy)
    except Exception:
        try:
            text = await asyncio.to_thread(_fetch_whisper, vid)
        except Exception as e:
            return f"Gagal ambil transkrip video {vid}: {e}"
    if not text or len(text) < 500:
        return "Transkrip kosong atau kependek, ga bisa diproses."

    url = f"https://www.youtube.com/watch?v={vid}"
    async with SessionLocal() as session:
        src = await session.scalar(select(Source).where(Source.name == "Manual YouTube"))
        if src is None:
            src = Source(
                name="Manual YouTube", type=SourceType.submission, base_url="youtube://manual"
            )
            session.add(src)
            await session.flush()
        h = content_hash(text)
        existing = await session.scalar(select(RawItem).where(RawItem.raw_hash == h))
        if existing is None:
            key = r2.raw_key(src.id, h)
            r2.put_text(key, text)
            item = RawItem(
                source_id=src.id, source_url=url, title=title,
                crawled_at=datetime.now(timezone.utc), r2_key_raw=key, raw_hash=h,
                raw_excerpt=text[:2000],
            )
            session.add(item)
            await session.flush()
            story = await process_raw_item(session, item)
            story_id = story.id if story else None
        else:
            story = await session.scalar(select(Story).where(Story.raw_item_id == existing.id))
            story_id = story.id if story else None
        await session.commit()

    if not story_id:
        return "Gagal proses jadi cerita."
    return await generate_and_deliver(story_id)


async def _safe_ingest(video: str) -> None:
    from app.notifier.telegram import send_text

    try:
        await _ingest_youtube(video)
    except Exception as e:
        log.error("ingest.failed", video=video, error=str(e))
        await send_text(f"Gagal proses video: {e}")


async def _exec(name: str, args: dict) -> str:
    if name == "ingest_youtube":
        asyncio.create_task(_safe_ingest(args.get("video", "")))
        return (
            "Oke, video lagi gue garap di background (transkrip, riset, bikin draft). "
            "Draftnya nanti otomatis masuk grup ya."
        )
    async with SessionLocal() as session:
        if name == "list_sources":
            rows = (await session.scalars(select(Source))).all()
            if not rows:
                return "Belum ada sumber."
            return "\n".join(
                f"#{s.id} [{s.status}] {s.type} - {s.name}" for s in rows
            )

        if name == "add_youtube_channel":
            channel = args["channel"].strip()
            src = await session.scalar(
                select(Source).where(Source.type == SourceType.youtube).limit(1)
            )
            if src is None:
                src = Source(
                    name="YouTube Watcher",
                    type=SourceType.youtube,
                    base_url="youtube://watcher",
                    parser_config={
                        "channels": [channel],
                        "years_ago": 1,
                        "max_per_channel": 5,
                        "transcript_mode": "caption_then_whisper",
                    },
                )
                session.add(src)
                await session.commit()
                return f"YouTube Watcher dibuat dengan channel {channel}."
            cfg = dict(src.parser_config or {})
            chans = list(cfg.get("channels") or [])
            if channel in chans:
                return f"Channel {channel} sudah ada. Total {len(chans)} channel."
            chans.append(channel)
            cfg["channels"] = chans
            src.parser_config = cfg
            await session.commit()
            return f"Channel {channel} ditambahkan. Total {len(chans)} channel."

        if name == "add_rss_source":
            session.add(
                Source(
                    name=args["name"],
                    type=SourceType.rss,
                    base_url=args["feed_url"],
                    parser_config={"feed_url": args["feed_url"], "fetch_full": True, "max_items": 20},
                )
            )
            await session.commit()
            return f"Sumber RSS '{args['name']}' ditambahkan."

        if name == "set_source_status":
            src = await _find_source(session, args["identifier"])
            if src is None:
                return "Sumber tidak ketemu."
            src.status = SourceStatus(args["status"])
            await session.commit()
            return f"Status '{src.name}' jadi {args['status']}."

        if name == "delete_source":
            src = await _find_source(session, args["identifier"])
            if src is None:
                return "Sumber tidak ketemu."
            nm = src.name
            await session.delete(src)
            await session.commit()
            return f"Sumber '{nm}' dihapus."

        if name == "list_candidates":
            limit = int(args.get("limit", 10))
            rows = (
                await session.execute(
                    select(Story.title, StoryScore.final_score, StoryScore.priority)
                    .join(StoryScore, StoryScore.story_id == Story.id)
                    .join(CandidateQueue, CandidateQueue.story_id == Story.id)
                    .where(CandidateQueue.status == StoryStatus.queued)
                    .order_by(StoryScore.final_score.desc())
                    .limit(limit)
                )
            ).all()
            if not rows:
                return "Belum ada kandidat di antrian."
            return "\n".join(
                f"[{r[2]} {round(r[1], 2)}] {r[0]}" for r in rows
            )

        if name == "stats":
            async def c(stmt):
                return int(await session.scalar(stmt) or 0)

            return json.dumps({
                "sources": await c(select(func.count(Source.id))),
                "stories": await c(select(func.count(Story.id))),
                "candidates": await c(select(func.count(CandidateQueue.id))),
                "knowledge": await c(select(func.count(Knowledge.id))),
            })

        if name == "add_knowledge":
            emb = None
            try:
                emb = client.embed([args["content"]])[0]
            except Exception as e:
                log.warning("admin.knowledge_embed_failed", error=str(e))
            session.add(Knowledge(title=args["title"], content=args["content"], embedding=emb))
            await session.commit()
            return f"Knowledge '{args['title']}' disimpan."

        if name == "search_knowledge":
            try:
                qv = client.embed([args["query"]])[0]
            except Exception:
                return "Gagal embed query."
            dist = Knowledge.embedding.cosine_distance(qv)
            rows = (
                await session.execute(
                    select(Knowledge.title, Knowledge.content)
                    .where(Knowledge.embedding.is_not(None))
                    .order_by(dist)
                    .limit(5)
                )
            ).all()
            if not rows:
                return "Belum ada knowledge yang cocok."
            return "\n".join(f"- {r[0]}: {r[1][:200]}" for r in rows)

    return f"Tool {name} tidak dikenal."


def _serialize_assistant(msg) -> dict:
    out: dict = {"role": "assistant", "content": msg.content or ""}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return out


async def run_admin_agent(chat_id: int, user_text: str) -> str:
    history = await load_history(chat_id)
    messages: list = [{"role": "system", "content": ADMIN_SYSTEM}, *history,
                      {"role": "user", "content": user_text}]
    reply = "Kebanyakan langkah, gue stop dulu."
    for _ in range(5):
        resp = await asyncio.to_thread(client.chat_raw, messages, TOOLS)
        msg = resp.choices[0].message  # type: ignore[union-attr]
        if not getattr(msg, "tool_calls", None):
            reply = msg.content or "(kosong)"
            break
        messages.append(_serialize_assistant(msg))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await _exec(tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    await append_turn(chat_id, "user", user_text)
    await append_turn(chat_id, "assistant", reply)
    await maybe_compact(chat_id)
    return reply
