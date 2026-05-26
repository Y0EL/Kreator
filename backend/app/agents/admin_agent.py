from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

from app.agents.memory import append_turn, load_history, maybe_compact
from app.db.enums import SourceStatus, SourceType, StoryStatus
from app.db.models import CandidateQueue, Knowledge, Source, Story, StoryScore
from app.db.session import SessionLocal
from app.services.sources import purge_source
from app.llm import client
from app.logging import get_logger

log = get_logger(__name__)

ADMIN_SYSTEM = (
    "Lo asisten admin sistem crawler konten horor punya Yoel, dengan AKSES ADMIN PENUH. "
    "PRINSIP UTAMA: EKSEKUSI LANGSUNG pakai tools, JANGAN banyak nanya, JANGAN minta konfirmasi "
    "berlebihan. Lo PUNYA kuasa buat ngelakuin semua aksi, jadi lakuin, jangan ragu.\n"
    "- Dikasih URL atau judul YouTube: LANGSUNG panggil ingest_youtube. Kalau user nyebut durasi "
    "(mis. '30-40 menit'), isi target_minutes (ambil angka tengah, mis. 35). JANGAN nanya tone, "
    "POV, verbatim, SFX, atau apa pun, sistem udah punya gaya naratif sendiri.\n"
    "- Diminta hapus sumber: LANGSUNG panggil delete_source (ini HAPUS PERMANEN beserta semua "
    "history). Jangan cuma arsip, jangan nanya ulang. Banyak sumber: panggil delete_source "
    "berulang. Pakai ID angka dari list_sources.\n"
    "- Kalau ga yakin sumber mana, panggil list_sources sendiri, jangan nanya user.\n"
    "- Diminta nyari atau nambah youtuber storytelling sejenis: panggil discover_youtube_channels "
    "dengan query yang pas, dia bakal nyari di YouTube dan nambah yang relevan sendiri. Kalau user "
    "minta 'semua' atau 'sebanyaknya', panggil beberapa kali dengan query beda (mis. 'cerita horor "
    "indonesia', 'misteri kriminal indonesia', 'creepypasta narasi indonesia').\n"
    "GAYA JAWABAN, WAJIB DIPATUHI: ngobrol santai gue/lo, dan SANGAT RINGKAS, maksimal 1 sampai 2 "
    "kalimat pendek. Cuma konfirmasi HASIL secara polos. DILARANG KERAS pakai emoji apa pun. "
    "DILARANG bikin daftar bullet, DILARANG bikin section model 'Catatan', 'Status', 'Nantinya'. "
    "DILARANG blok kode atau tag <pre> atau <code>. JANGAN ngulang detail yang user udah tau "
    "(URL, durasi, dsb), JANGAN basa-basi. Boleh <b>tebal</b> seperlunya doang. "
    "Jangan ngarang, pakai tool buat data nyata. "
    "DILARANG KERAS em dash, en dash, titik koma. Pakai hubung biasa atau koma."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_sources",
        "description": "Lihat semua sumber crawl beserta status dan tipe.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "ingest_youtube",
        "description": "Ambil SATU video YouTube (URL atau judul), transkrip, lalu langsung bikin "
                       "draft skrip versi sendiri dan kirim ke grup. Panggil langsung tanpa nanya.",
        "parameters": {"type": "object", "properties": {
            "video": {"type": "string", "description": "URL video YouTube atau judul"},
            "target_minutes": {"type": "integer", "description": "durasi target skrip (menit), opsional"}},
            "required": ["video"]},
    }},
    {"type": "function", "function": {
        "name": "add_youtube_channel",
        "description": "Tambah channel YouTube untuk dipantau (handle @nama, URL, atau channelId UC...).",
        "parameters": {"type": "object", "properties": {
            "channel": {"type": "string"}}, "required": ["channel"]},
    }},
    {"type": "function", "function": {
        "name": "discover_youtube_channels",
        "description": "Cari channel YouTube storytelling horor/misteri yang relevan lewat YouTube, "
                       "lalu LANGSUNG tambahin yang ketemu ke daftar pantauan. Pakai kalau user minta "
                       "nyariin atau nambah youtuber sejenis secara dinamis.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "kata kunci, mis. 'cerita horor misteri storytelling indonesia'"},
            "max": {"type": "integer", "description": "jumlah channel maksimal yang ditambah, default 5"}}},
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
        "description": "HAPUS PERMANEN sumber beserta semua history-nya (raw item, story, script). "
                       "by id angka atau nama. Eksekusi langsung kalau diminta hapus.",
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
    ident = str(identifier).strip().lstrip("#").strip()
    if ident.isdigit():
        return await session.get(Source, int(ident))
    return await session.scalar(select(Source).where(Source.name.ilike(f"%{ident}%")))


async def _safe_ingest(video: str, target_minutes: int | None = None) -> None:
    from app.notifier.telegram import send_text
    from app.services.youtube_ingest import ingest_youtube

    try:
        await ingest_youtube(video, target_minutes)
    except Exception as e:
        log.error("ingest.failed", video=video, error=str(e))
        await send_text(f"Gagal proses video: {e}")


async def _exec(name: str, args: dict) -> str:
    if name == "ingest_youtube":
        asyncio.create_task(_safe_ingest(args.get("video", ""), args.get("target_minutes")))
        return "Oke, video lagi gue garap di background. Draftnya nanti otomatis masuk grup."
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

        if name == "discover_youtube_channels":
            from app.config import get_settings

            key = get_settings().youtube_api_key
            if not key:
                return "YOUTUBE_API_KEY belum di-set, ga bisa nyari channel."
            query = (args.get("query") or "cerita horor misteri storytelling indonesia").strip()
            maxn = max(1, min(int(args.get("max", 5)), 10))
            import httpx

            async with httpx.AsyncClient(timeout=20) as hc:
                r = await hc.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={"part": "snippet", "type": "channel", "q": query,
                            "maxResults": maxn, "key": key},
                )
                found = r.json().get("items", [])
            src = await session.scalar(
                select(Source).where(Source.type == SourceType.youtube).limit(1)
            )
            if src is None:
                src = Source(
                    name="YouTube Watcher", type=SourceType.youtube,
                    base_url="youtube://watcher",
                    parser_config={"channels": [], "max_per_channel": 10},
                )
                session.add(src)
                await session.flush()
            cfg = dict(src.parser_config or {})
            chans = list(cfg.get("channels") or [])
            added = []
            for it in found:
                cid = it.get("id", {}).get("channelId")
                title = it.get("snippet", {}).get("title")
                if cid and cid not in chans:
                    chans.append(cid)
                    added.append(title or cid)
            cfg["channels"] = chans
            src.parser_config = cfg
            await session.commit()
            if not added:
                return f"Ga nemu channel baru buat '{query}'."
            return f"Nambah {len(added)} channel: {', '.join(added)}. Total {len(chans)} dipantau."

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
                return "Sumber ga ketemu."
            purged = await purge_source(session, src.id)
            return f"Sumber '{purged}' dihapus permanen beserta semua history-nya."

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
