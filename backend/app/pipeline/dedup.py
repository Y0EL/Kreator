from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Story
from app.logging import get_logger

log = get_logger(__name__)

SIMILARITY_DISTANCE_THRESHOLD = 0.15


async def nearest(
    session: AsyncSession, embedding: list[float], exclude_id: int, limit: int = 5
) -> list[tuple[int, int | None, float]]:
    dist = Story.embedding.cosine_distance(embedding)
    rows = (
        await session.execute(
            select(Story.id, Story.cluster_id, dist.label("d"))
            .where(Story.id != exclude_id, Story.embedding.is_not(None))
            .order_by(dist)
            .limit(limit)
        )
    ).all()
    return [(r[0], r[1], float(r[2])) for r in rows]


async def assign_cluster(session: AsyncSession, story: Story) -> float:
    if story.embedding is None:
        story.cluster_id = story.id
        story.is_primary = True
        return 1.0

    neighbors = await nearest(session, story.embedding, exclude_id=story.id)
    if neighbors and neighbors[0][2] < SIMILARITY_DISTANCE_THRESHOLD:
        match_id, match_cluster, distance = neighbors[0]
        story.cluster_id = match_cluster or match_id
        story.is_primary = False
        log.info("dedup.duplicate", story_id=story.id, cluster=story.cluster_id, dist=distance)
        return distance

    story.cluster_id = story.id
    story.is_primary = True
    return neighbors[0][2] if neighbors else 1.0
