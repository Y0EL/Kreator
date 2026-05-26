from __future__ import annotations

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research_agent import run_research
from app.db.enums import ScriptStatus, StoryStatus
from app.db.models import RawItem, ResearchPack, Script, Story
from app.integrations import drive
from app.llm import client
from app.llm.prompts import (
    DRAFT_SYSTEM,
    OUTLINE_SYSTEM,
    OUTLINE_USER,
    SEGMENT_EXPAND_USER,
    SEGMENT_USER,
)
from app.logging import get_logger
from app.services import progress
from app.util.textfix import sanitize_script
from app.voice import retrieve

log = get_logger(__name__)

_WPM = 135
_WRITER_TIER = "cheap"
_MIN_RATIO = 0.7
_MAX_EXPANSIONS = 5


def _seg_budgets(outline: dict, total_words: int) -> list[dict]:
    segs = outline.get("segments") or []
    if not segs:
        return [{"name": "CERITA", "tone": "naratif", "poin": [], "target_words": total_words}]
    weights: list[float] = []
    for s in segs:
        try:
            w = float(s.get("durasi") or 0)
        except (TypeError, ValueError):
            w = 0.0
        weights.append(w if w > 0 else 1.0)
    tot = sum(weights) or 1.0
    out: list[dict] = []
    for s, w in zip(segs, weights):
        out.append(
            {
                "name": str(s.get("name") or "SEGMEN"),
                "tone": str(s.get("tone") or ""),
                "poin": s.get("poin") or [],
                "target_words": max(150, int(total_words * w / tot)),
            }
        )
    return out


def _tail(written: list[tuple[str, str]], max_words: int) -> str:
    if not written:
        return "(belum ada, ini bagian pembuka)"
    joined = "\n\n".join(t for _, t in written)
    words = joined.split()
    if len(words) <= max_words:
        return joined
    return "... " + " ".join(words[-max_words:])


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

    total_words = max(700, int(minutes) * _WPM)
    ledger = _evidence_text(pack, story)
    voice = retrieve.voice_card_text(card)
    exem = "\n\n---\n\n".join(exemplars) if exemplars else "(tidak ada contoh)"
    budgets = _seg_budgets(outline, total_words)
    n = len(budgets)

    written: list[tuple[str, str]] = []
    for i, seg in enumerate(budgets):
        progress.step(
            f"Menulis segmen {i + 1}/{n}: {seg['name']}",
            80 + int(11 * i / n),
            story_id=story.id,
        )
        text = await asyncio.to_thread(
            client.complete,
            system=DRAFT_SYSTEM,
            user=SEGMENT_USER.format(
                voice_card=voice,
                exemplars=exem,
                ledger=ledger,
                previous=_tail(written, 700),
                name=seg["name"],
                tone=seg["tone"] or "naratif, menegangkan",
                poin="\n".join(f"- {p}" for p in seg["poin"]) or "-",
                target_words=seg["target_words"],
            ),
            tier=_WRITER_TIER,
            temperature=0.8,
            max_tokens=min(8000, seg["target_words"] * 4 + 200),
        )
        written.append((seg["name"], sanitize_script(text).strip()))

    progress.step("Cek panjang dan rapikan", 92, story_id=story.id)
    expansions = 0
    for i, seg in enumerate(budgets):
        if expansions >= _MAX_EXPANSIONS:
            break
        name, text = written[i]
        wc = len(text.split())
        if wc < int(seg["target_words"] * _MIN_RATIO):
            expanded = await asyncio.to_thread(
                client.complete,
                system=DRAFT_SYSTEM,
                user=SEGMENT_EXPAND_USER.format(
                    name=name,
                    target_words=seg["target_words"],
                    ledger=ledger,
                    previous=_tail(written[:i], 700),
                    current=text,
                ),
                tier=_WRITER_TIER,
                temperature=0.8,
                max_tokens=min(8000, seg["target_words"] * 4 + 200),
            )
            expanded = sanitize_script(expanded).strip()
            if len(expanded.split()) > wc:
                written[i] = (name, expanded)
                expansions += 1

    draft_text = sanitize_script(
        "\n\n".join(f"[SEGMEN: {name}]\n{text}" for name, text in written)
    )
    word_count = len(draft_text.split())
    log.info(
        "script.draft_segments",
        story_id=story.id,
        segments=n,
        words=word_count,
        target=total_words,
        expansions=expansions,
    )

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
    session: AsyncSession, story: Story, persona: str | None = None, web_search: bool = False
) -> Script:
    persona = await _pick_persona(session, persona)
    progress.step("Riset sumber", 64, story_id=story.id)
    pack = await run_research(session, story, web_search=web_search)
    progress.step("Menyusun outline", 76, story_id=story.id)
    outline = await generate_outline(story, pack)
    progress.step("Menulis draft", 85, story_id=story.id)
    script = await generate_draft(session, story, pack, outline, persona)
    await session.commit()
    return script


async def rewrite_draft(
    session: AsyncSession,
    story: Story,
    note: str,
    persona: str | None = None,
    web_search: bool = False,
) -> Script:
    persona = await _pick_persona(session, persona)
    if web_search:
        pack = await run_research(session, story, web_search=True)
    else:
        pack = await session.scalar(
            select(ResearchPack).where(ResearchPack.story_id == story.id)
        )
    progress.step("Menyusun outline", 76, story_id=story.id)
    outline = await generate_outline(story, pack)
    progress.step("Menulis ulang draft", 85, story_id=story.id)
    outline["rewrite_note"] = note
    script = await generate_draft(session, story, pack, outline, persona)
    script.rewrite_note = note
    script.status = ScriptStatus.revised
    await session.commit()
    return script
