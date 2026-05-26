from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.agents.script_pipeline import render_sources, run_full_generation
from app.crawler.runner import crawl_active_sources
from app.db.enums import Priority, SourceType, StoryStatus
from app.db.init_db import init_db
from app.db.models import CandidateQueue, RawItem, ResearchPack, Script, Source, Story, StoryScore
from app.db.session import SessionLocal
from app.export.document import build_docx, build_pdf
from app.integrations import r2
from app.logging import configure_logging, get_logger
from app.notifier.telegram import draft_keyboard, send_digest, send_document
from app.pipeline.processor import process_new, rescore_existing
from app.seeds import seed_sources
from app.util.hashing import content_hash
from app.voice.builder import build_voice_profiles

SAMPLE_TITLE = "Suara Tangisan di Kontrakan Blok C"
SAMPLE_TEXT = """Aku pindah ke kontrakan petak di Blok C itu karena harganya murah dan dekat tempat kerja baruku. Pemilik kontrakan, seorang ibu tua, hanya berpesan satu hal saat menyerahkan kunci: jangan pernah membuka jendela kamar belakang setelah jam dua belas malam. Aku pikir itu cuma pesan klise orang tua, jadi aku iyakan saja sambil tersenyum.

Malam pertama berjalan biasa. Malam kedua aku mulai mendengarnya. Suara tangisan perempuan, pelan, datang dari arah kamar belakang. Aku kira itu tetangga, tapi saat kuketuk dinding, suaranya berhenti, lalu pindah. Seolah sumbernya tahu aku sedang mendengarkan dan sengaja menjauh.

Hari ketiga aku bertanya pada tetangga sebelah. Wajahnya langsung berubah. Dia bilang kontrakan yang kutempati dulu dihuni seorang perempuan muda yang hilang tanpa jejak tujuh tahun lalu. Barang-barangnya masih utuh, pintunya terkunci dari dalam, tapi orangnya raib. Yang terakhir mendengar suaranya bilang, dia menangis semalaman sebelum akhirnya senyap.

Aku mencoba bertahan. Tapi malam itu, tepat jam dua belas, tangisan itu terdengar paling jelas. Dan untuk pertama kalinya, aku sadar jendela kamar belakang yang seharusnya kukunci, perlahan terbuka sendiri. Angin masuk membawa bau tanah basah. Di kaca yang berembun, ada bekas telapak tangan kecil dari sisi dalam, seakan ada yang ingin keluar dari sana sejak lama.

Aku tidak pernah tidur di kontrakan itu lagi. Tapi sampai sekarang, setiap jam dua belas malam, aku masih sering terbangun. Dan kadang, di keheningan kamar baruku yang jauh dari Blok C, aku masih mendengar tangisan itu. Semakin dekat."""

log = get_logger(__name__)


async def _count(session, stmt) -> int:
    return int(await session.scalar(stmt) or 0)


async def metrics() -> dict:
    async with SessionLocal() as session:
        raw = await _count(session, select(func.count(RawItem.id)))
        stories = await _count(session, select(func.count(Story.id)))
        primary = await _count(
            session, select(func.count(Story.id)).where(Story.is_primary.is_(True))
        )
        dupes = await _count(
            session, select(func.count(Story.id)).where(Story.is_primary.is_(False))
        )
        queued = await _count(session, select(func.count(CandidateQueue.id)))
        avg_score = await session.scalar(select(func.avg(StoryScore.final_score)))
        by_priority = {}
        for p in Priority:
            by_priority[p.value] = await _count(
                session, select(func.count(StoryScore.id)).where(StoryScore.priority == p)
            )
        return {
            "raw_items": raw,
            "stories": stories,
            "primary": primary,
            "duplicates": dupes,
            "dedup_ratio": round(dupes / stories, 3) if stories else 0.0,
            "queued_candidates": queued,
            "avg_final_score": round(float(avg_score), 4) if avg_score is not None else None,
            "by_priority": by_priority,
        }


async def run_crawl() -> None:
    t0 = time.monotonic()
    async with SessionLocal() as session:
        jobs = await crawl_active_sources(session)
    found = sum(j.items_found for j in jobs)
    new = sum(j.items_new for j in jobs)
    log.info("stress.crawl", jobs=len(jobs), found=found, new=new, secs=round(time.monotonic() - t0, 1))


async def run_process(limit: int = 200) -> None:
    t0 = time.monotonic()
    async with SessionLocal() as session:
        created = await process_new(session, limit=limit)
    log.info("stress.process", created=created, secs=round(time.monotonic() - t0, 1))


async def run_rescore() -> None:
    t0 = time.monotonic()
    async with SessionLocal() as session:
        queued = await rescore_existing(session)
    log.info("stress.rescore", queued=queued, secs=round(time.monotonic() - t0, 1))


async def run_cleantext() -> None:
    from app.db.models import ResearchPack as RP
    from app.db.models import StoryPitch
    from app.util.textfix import sanitize_script

    def cl(v):
        return sanitize_script(v) if isinstance(v, str) else v

    def cll(v):
        return [sanitize_script(x) if isinstance(x, str) else x for x in v] if isinstance(v, list) else v

    async with SessionLocal() as session:
        stories = (await session.scalars(select(Story))).all()
        for st in stories:
            st.summary = cl(st.summary)
            st.subtopics = cll(st.subtopics)
            st.timeline = cll(st.timeline)
        for p in (await session.scalars(select(StoryPitch))).all():
            p.hook = cl(p.hook)
            p.viral_label = cl(p.viral_label)
            p.where_from = cl(p.where_from)
            p.reasons = cll(p.reasons)
        for rp in (await session.scalars(select(RP))).all():
            rp.core_summary = cl(rp.core_summary)
            rp.angle = cl(rp.angle)
            rp.confidence_notes = cl(rp.confidence_notes)
            rp.proven = cll(rp.proven)
            rp.speculative = cll(rp.speculative)
            rp.open_loops = cll(rp.open_loops)
            rp.timeline = cll(rp.timeline)
        await session.commit()
    log.info("stress.cleantext", stories=len(stories))


async def run_voice() -> None:
    async with SessionLocal() as session:
        result = await build_voice_profiles(session)
    log.info("stress.voice", profiles=result)


async def run_script() -> None:
    async with SessionLocal() as session:
        story = await session.scalar(
            select(Story)
            .join(StoryScore, StoryScore.story_id == Story.id)
            .join(CandidateQueue, CandidateQueue.story_id == Story.id)
            .where(CandidateQueue.status == StoryStatus.queued)
            .order_by(StoryScore.final_score.desc())
            .limit(1)
        )
        if story is None:
            log.warning("stress.script.no_candidate")
            return
        t0 = time.monotonic()
        script = await run_full_generation(session, story)
        preview = (script.draft or "")[:600]
        log.info(
            "stress.script",
            story_id=story.id,
            version=script.version,
            persona=script.voice_persona,
            chars=len(script.draft or ""),
            drive=script.drive_url,
            secs=round(time.monotonic() - t0, 1),
        )
        print("\n----- DRAFT PREVIEW -----\n" + preview + "\n-------------------------\n")


async def run_senddraft(story_id: int) -> None:
    import re

    async with SessionLocal() as session:
        story = await session.get(Story, story_id)
        if story is None:
            log.warning("senddraft.no_story", story_id=story_id)
            return
        script = await session.scalar(
            select(Script).where(Script.story_id == story_id).order_by(Script.version.desc())
        )
        if script is None or not script.draft:
            log.warning("senddraft.no_draft", story_id=story_id)
            return
        pack = await session.scalar(
            select(ResearchPack).where(ResearchPack.story_id == story_id)
        )
        sources = await render_sources(session, story, pack)
        title = f"{story.title or 'Untitled'} (story {story_id})"
        meta = [
            f"Persona: {script.voice_persona}",
            f"Durasi target: sekitar {script.estimated_minutes} menit",
            f"Versi: v{script.version}",
        ]
        body = script.draft
        version = script.version

    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "draft"
    docx = build_docx(title, body, sources, meta)
    await send_document(
        docx,
        f"{base}.docx",
        caption=f"📄 Draft v{version}: {title}",
        reply_markup=draft_keyboard(story_id),
    )
    try:
        pdf = build_pdf(title, body, sources, meta)
        await send_document(pdf, f"{base}.pdf", caption="PDF buat dibaca")
    except Exception as e:
        log.warning("senddraft.pdf_failed", story_id=story_id, error=str(e))
    log.info("senddraft.done", story_id=story_id, version=version)


async def run_digest() -> None:
    async with SessionLocal() as session:
        n = await send_digest(session)
    log.info("stress.digest", sent=n)


async def run_sample() -> None:
    async with SessionLocal() as session:
        source = await session.scalar(select(Source).where(Source.name == "Manual Sample"))
        if source is None:
            source = Source(
                name="Manual Sample", type=SourceType.submission, base_url="local://sample"
            )
            session.add(source)
            await session.flush()
        h = content_hash(SAMPLE_TEXT)
        exists = await session.scalar(select(RawItem.id).where(RawItem.raw_hash == h))
        if exists is None:
            key = r2.raw_key(source.id, h)
            r2.put_text(key, SAMPLE_TEXT)
            session.add(
                RawItem(
                    source_id=source.id,
                    source_url="local://sample/1",
                    title=SAMPLE_TITLE,
                    crawled_at=datetime.now(tz=timezone.utc),
                    r2_key_raw=key,
                    raw_hash=h,
                    raw_excerpt=SAMPLE_TEXT[:2000],
                    reply_count=320,
                    view_count=48000,
                )
            )
        await session.commit()
    log.info("stress.sample.done")


async def run_all(drop: bool) -> None:
    await init_db(drop=drop)
    async with SessionLocal() as session:
        await seed_sources(session)
    await run_sample()
    await run_crawl()
    await run_process()
    await run_voice()
    await run_script()
    print("\nMETRICS:", await metrics())


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "initdb", "seed", "sample", "crawl", "process", "rescore", "cleantext", "voice",
            "script", "digest", "senddraft", "metrics", "all"
        ],
    )
    parser.add_argument("--drop", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--story", type=int, default=0)
    args = parser.parse_args()

    async def dispatch() -> None:
        if args.command == "initdb":
            await init_db(drop=args.drop)
        elif args.command == "seed":
            async with SessionLocal() as session:
                await seed_sources(session)
        elif args.command == "sample":
            await run_sample()
        elif args.command == "crawl":
            await run_crawl()
        elif args.command == "process":
            await run_process(limit=args.limit)
        elif args.command == "rescore":
            await run_rescore()
        elif args.command == "cleantext":
            await run_cleantext()
        elif args.command == "voice":
            await run_voice()
        elif args.command == "script":
            await run_script()
        elif args.command == "digest":
            await run_digest()
        elif args.command == "senddraft":
            await run_senddraft(args.story)
        elif args.command == "metrics":
            print(await metrics())
        elif args.command == "all":
            await run_all(drop=args.drop)

    asyncio.run(dispatch())


if __name__ == "__main__":
    main()
