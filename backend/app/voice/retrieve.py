from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VoiceExemplar, VoiceProfile
from app.logging import get_logger

log = get_logger(__name__)


async def list_personas(session: AsyncSession) -> list[str]:
    return list((await session.scalars(select(VoiceProfile.persona))).all())


async def get_voice_card(session: AsyncSession, persona: str) -> dict:
    profile = await session.scalar(select(VoiceProfile).where(VoiceProfile.persona == persona))
    return profile.voice_card if profile else {}


def voice_card_text(card: dict) -> str:
    return json.dumps(card, ensure_ascii=False, indent=2) if card else "(belum ada voice card)"


async def retrieve_exemplars(
    session: AsyncSession, persona: str, query_embedding: list[float] | None, k: int = 3
) -> list[str]:
    stmt = select(VoiceExemplar.chunk_text).where(VoiceExemplar.persona == persona)
    if query_embedding is not None:
        dist = VoiceExemplar.embedding.cosine_distance(query_embedding)
        stmt = stmt.where(VoiceExemplar.embedding.is_not(None)).order_by(dist)
    stmt = stmt.limit(k)
    return list((await session.scalars(stmt)).all())


async def retrieve_exemplars_blend(
    session: AsyncSession, query_embedding: list[float] | None, k: int = 6
) -> list[str]:
    stmt = select(VoiceExemplar.chunk_text)
    if query_embedding is not None:
        dist = VoiceExemplar.embedding.cosine_distance(query_embedding)
        stmt = stmt.where(VoiceExemplar.embedding.is_not(None)).order_by(dist)
    stmt = stmt.limit(k)
    return list((await session.scalars(stmt)).all())
