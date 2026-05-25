from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research_agent import run_research
from app.db.enums import ScriptStatus, StoryStatus
from app.db.models import RawItem, ResearchPack, Script, Story
from app.integrations import drive
from app.llm import client
from app.llm.prompts import DRAFT_SYSTEM, DRAFT_USER, OUTLINE_SYSTEM, OUTLINE_USER
from app.logging import get_logger
from app.services import progress
from app.util.textfix import sanitize_script
from app.voice import retrieve

log = get_logger(__name__)


def _evidence_text(pack: ResearchPack | None, story: Story) -> str:
    if pack is None:
        return f"Inti cerita: {story.summary or story.cleaned_text[:1500]}"
    return json.dumps(
        {
            "inti_cerita": pack.core_summary,
            "urutan_kejadian": pack.timeline,
            "detail_penting": pack.proven,
            "bagian_misterius": pack.speculative,
            "rasa_penasaran": pack.open_loops,
            "sudut_cerita": pack.angle,
        },
        ensure_ascii=False,
        indent=2,
    )


async def render_sources(session: AsyncSession, story: Story, pack: ResearchPack | None) -> str:
    src_url = await session.scalar(
        select(RawItem.source_url).where(RawItem.id == story.raw_item_id)
    )
    lines = ["=== SUMBER DAN BUKTI (referensi, bukan untuk dibacakan) ==="]
    lines.append(f"Sumber utama (asal cerita): {src_url or 'tidak diketahui'}")
    supporting = (pack.sources if pack else None) or []
    if supporting:
        lines.append("")
        lines.append("Sumber pendukung:")
        for s in supporting:
            if isinstance(s, dict):
                label = s.get("label") or s.get("sumber") or ""
                note = s.get("catatan") or s.get("link") or s.get("url") or ""
                entry = f"- {label}: {note}".rstrip(": ").rstrip()
                lines.append(entry)
            else:
                lines.append(f"- {s}")
    proven = (pack.proven if pack else None) or []
    if proven:
        lines.append("")
        lines.append("Bagian yang relatif terbukti:")
        lines.extend(f"- {p}" for p in proven)
    speculative = (pack.speculative if pack else None) or []
    if speculative:
        lines.append("")
        lines.append("Bagian yang masih spekulatif:")
        lines.extend(f"- {p}" for p in speculative)
    if pack and pack.confidence_notes:
        lines.append("")
        lines.append(f"Catatan keandalan: {pack.confidence_notes}")
    return sanitize_script("\n".join(lines))


async def _pick_persona(session: AsyncSession, persona: str | None) -> str:
    if persona:
        return persona
    personas = await retrieve.list_personas(session)
    return personas[0] if personas else "default"


async def generate_outline(story: Story, pack: ResearchPack | None) -> dict:
    story.status = StoryStatus.outline
    minutes = story.estimated_minutes or 15
    return client.complete_json(
        system=OUTLINE_SYSTEM,
        user=OUTLINE_USER.format(minutes=minutes, evidence=_evidence_text(pack, story)),
        tier="quality",
        temperature=0.5,
    )


async def generate_draft(
    session: AsyncSession,
    story: Story,
    pack: ResearchPack | None,
    outline: dict,
    persona: str,
) -> Script:
    minutes = story.estimated_minutes or 15
    card = await retrieve.get_voice_card(session, persona)
    exemplars = await retrieve.retrieve_exemplars(
        session, persona, query_embedding=story.embedding, k=5
    )

    draft_text = client.complete(
        system=DRAFT_SYSTEM,
        user=DRAFT_USER.format(
            minutes=minutes,
            persona=persona,
            voice_card=retrieve.voice_card_text(card),
            exemplars="\n\n---\n\n".join(exemplars) if exemplars else "(tidak ada contoh)",
            outline=json.dumps(outline, ensure_ascii=False, indent=2),
            evidence=_evidence_text(pack, story),
        ),
        tier="quality",
        temperature=0.8,
    )
    draft_text = sanitize_script(draft_text)

    next_version = (
        await session.scalar(
            select(Script.version)
            .where(Script.story_id == story.id)
            .order_by(Script.version.desc())
        )
        or 0
    ) + 1
    script = Script(
        story_id=story.id,
        version=next_version,
        status=ScriptStatus.draft,
        outline=outline,
        draft=draft_text,
        voice_persona=persona,
        estimated_minutes=minutes,
    )
    footer = sanitize_script(await render_sources(session, story, pack))
    doc = f"{draft_text}\n\n\n{footer}"
    title = f"DRAFT v{next_version} - {story.title or 'Untitled'} (story {story.id})"
    script.drive_url = drive.save_doc(title, doc)
    session.add(script)
    story.status = StoryStatus.draft
    log.info("script.draft_done", story_id=story.id, version=next_version, drive=script.drive_url)
    return script


async def run_full_generation(
    session: AsyncSession, story: Story, persona: str | None = None
) -> Script:
    persona = await _pick_persona(session, persona)
    progress.step("Riset sumber", 64, story_id=story.id)
    pack = await run_research(session, story)
    progress.step("Menyusun outline", 76, story_id=story.id)
    outline = await generate_outline(story, pack)
    progress.step("Menulis draft", 85, story_id=story.id)
    script = await generate_draft(session, story, pack, outline, persona)
    await session.commit()
    return script


async def rewrite_draft(
    session: AsyncSession, story: Story, note: str, persona: str | None = None
) -> Script:
    persona = await _pick_persona(session, persona)
    pack = await session.scalar(select(ResearchPack).where(ResearchPack.story_id == story.id))
    progress.step("Menyusun outline", 76, story_id=story.id)
    outline = await generate_outline(story, pack)
    progress.step("Menulis ulang draft", 85, story_id=story.id)
    outline["rewrite_note"] = note
    script = await generate_draft(session, story, pack, outline, persona)
    script.rewrite_note = note
    script.status = ScriptStatus.revised
    await session.commit()
    return script
