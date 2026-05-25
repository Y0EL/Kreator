from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import StoryStatus
from app.db.models import ResearchPack, Story
from app.integrations import drive
from app.llm import client
from app.llm.prompts import RESEARCH_SYSTEM, RESEARCH_USER
from app.logging import get_logger
from app.services import progress
from app.util.textfix import sanitize_script

log = get_logger(__name__)
_MAX_CHARS = 16000


async def run_research(
    session: AsyncSession, story: Story, web_search: bool = False
) -> ResearchPack:
    story.status = StoryStatus.researching
    extra = ""
    if web_search:
        progress.step("Cari fakta di web", 60, story_id=story.id)
        query = f"{story.title or ''}. {story.summary or story.cleaned_text[:600]}"
        findings = await asyncio.to_thread(client.web_search, query)
        if findings:
            extra = (
                "\n\nINFORMASI TAMBAHAN DARI WEB (utamakan ini bila lebih akurat dan terbaru):\n"
                + findings
            )
    data = client.complete_json(
        system=RESEARCH_SYSTEM,
        user=RESEARCH_USER.format(text=story.cleaned_text[:_MAX_CHARS]) + extra,
        tier="quality",
        temperature=0.4,
    )

    pack = await session.scalar(select(ResearchPack).where(ResearchPack.story_id == story.id))
    if pack is None:
        pack = ResearchPack(story_id=story.id)
        session.add(pack)

    pack.core_summary = data.get("core_summary")
    pack.timeline = data.get("timeline") or []
    pack.sources = data.get("sources") or []
    pack.proven = data.get("proven") or []
    pack.speculative = data.get("speculative") or []
    pack.open_loops = data.get("open_loops") or []
    pack.angle = data.get("angle")
    pack.confidence_notes = data.get("confidence_notes")

    title = f"RESEARCH - {story.title or 'Untitled'} (story {story.id})"
    pack.drive_url = drive.save_doc(title, sanitize_script(_render(pack)))
    log.info("research.done", story_id=story.id, drive=pack.drive_url)
    return pack


def _render(p: ResearchPack) -> str:
    def block(label: str, items: list) -> str:
        body = "\n".join(f"- {x}" for x in items) if items else "-"
        return f"## {label}\n{body}\n"

    return "\n".join(
        [
            f"## Inti\n{p.core_summary or '-'}\n",
            block("Timeline", p.timeline),
            block("Sumber", [s.get("label", s) if isinstance(s, dict) else s for s in p.sources]),
            block("Terbukti", p.proven),
            block("Spekulatif", p.speculative),
            block("Open loops (hook)", p.open_loops),
            f"## Angle\n{p.angle or '-'}\n",
            f"## Catatan confidence\n{p.confidence_notes or '-'}\n",
        ]
    )
