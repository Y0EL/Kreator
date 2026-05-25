from __future__ import annotations

import re

from sqlalchemy import select

from app.agents.script_pipeline import render_sources, rewrite_draft, run_full_generation
from app.db.models import ResearchPack, Story
from app.db.session import SessionLocal
from app.export.document import build_docx, build_pdf
from app.logging import get_logger
from app.notifier.telegram import draft_keyboard, send_document, send_text
from app.services import progress

log = get_logger(__name__)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "draft"


async def generate_and_deliver(story_id: int, note: str | None = None) -> str:
    async with SessionLocal() as session:
        story = await session.get(Story, story_id)
        if story is None:
            await send_text("Cerita ga ketemu.")
            return "story not found"
        if note:
            script = await rewrite_draft(session, story, note)
        else:
            script = await run_full_generation(session, story)
        pack = await session.scalar(select(ResearchPack).where(ResearchPack.story_id == story_id))
        sources = await render_sources(session, story, pack)
        story_title = story.title or "Untitled"
        title = f"{story_title} (story {story_id})"
        meta = [
            f"Persona: {script.voice_persona}",
            f"Durasi target: sekitar {script.estimated_minutes} menit",
            f"Versi: v{script.version}",
        ]
        body = script.draft or ""
        version = script.version

    progress.step("Render dokumen", 94, story_id=story_id, title=story_title)
    base = _slug(title)
    docx = build_docx(title, body, sources, meta)
    progress.step("Mengirim ke grup", 98, story_id=story_id, title=story_title)
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
        log.warning("delivery.pdf_failed", story_id=story_id, error=str(e))
    progress.done(story_title)
    return f"Draft v{version} buat '{title}' udah dibikin dan dikirim ke grup."
