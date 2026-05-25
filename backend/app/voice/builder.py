from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VoiceExemplar, VoiceProfile
from app.llm import client
from app.llm.prompts import VOICE_CARD_SYSTEM, VOICE_CARD_USER
from app.logging import get_logger
from app.voice.transcript import chunk_text, load_corpus

log = get_logger(__name__)

_DEFAULT_LESSON_DIR = Path(__file__).resolve().parents[3] / "lesson"
_VOICE_CARD_SAMPLE_CHARS = 8000
_EMBED_BATCH = 50


def _distill_voice_card(sample_text: str) -> dict:
    return client.complete_json(
        system=VOICE_CARD_SYSTEM,
        user=VOICE_CARD_USER.format(text=sample_text[:_VOICE_CARD_SAMPLE_CHARS]),
        tier="cheap",
        temperature=0.2,
    )


async def build_voice_profiles(
    session: AsyncSession, lesson_dir: str | Path = _DEFAULT_LESSON_DIR
) -> dict[str, int]:
    corpus = load_corpus(lesson_dir)
    result: dict[str, int] = {}

    for persona, files in corpus.items():
        sample = "\n\n".join(text[:4000] for _, text in files[:2])
        try:
            voice_card = _distill_voice_card(sample)
        except Exception as e:
            log.error("voice.card_failed", persona=persona, error=str(e))
            voice_card = {}

        await session.execute(delete(VoiceExemplar).where(VoiceExemplar.persona == persona))

        chunks: list[tuple[str, str]] = []
        for fname, text in files:
            for ch in chunk_text(text):
                chunks.append((fname, ch))

        n = 0
        for start in range(0, len(chunks), _EMBED_BATCH):
            batch = chunks[start : start + _EMBED_BATCH]
            try:
                vectors = client.embed([c for _, c in batch])
            except Exception as e:
                log.error("voice.embed_failed", persona=persona, error=str(e))
                vectors = [None] * len(batch)  # type: ignore[list-item]
            for (fname, ch), vec in zip(batch, vectors, strict=True):
                session.add(
                    VoiceExemplar(
                        persona=persona, source_file=fname, chunk_text=ch, embedding=vec
                    )
                )
                n += 1

        profile = await session.scalar(
            select(VoiceProfile).where(VoiceProfile.persona == persona)
        )
        if profile is None:
            profile = VoiceProfile(persona=persona)
            session.add(profile)
        profile.voice_card = voice_card
        profile.source_files = [f for f, _ in files]

        await session.commit()
        result[persona] = n
        log.info("voice.profile_built", persona=persona, exemplars=n)

    return result
