from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.db.base import Base, TimestampMixin
from app.db.enums import (
    Confidence,
    CrawlJobStatus,
    Decision,
    Priority,
    ScriptStatus,
    SourceStatus,
    SourceType,
    StoryStatus,
)

EMBED_DIM = get_settings().llm_embedding_dim


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[SourceType] = mapped_column(String(32))
    base_url: Mapped[str] = mapped_column(String(1000))
    status: Mapped[SourceStatus] = mapped_column(String(16), default=SourceStatus.active)
    parser_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=720)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)
    last_crawled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    crawl_jobs: Mapped[list[CrawlJob]] = relationship(back_populates="source")
    raw_items: Mapped[list[RawItem]] = relationship(back_populates="source")


class CrawlJob(Base, TimestampMixin):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[CrawlJobStatus] = mapped_column(String(16), default=CrawlJobStatus.pending)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = relationship(back_populates="crawl_jobs")


class RawItem(Base, TimestampMixin):
    __tablename__ = "raw_items"
    __table_args__ = (UniqueConstraint("raw_hash", name="uq_raw_items_raw_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    source_url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    crawled_at: Mapped[datetime] = mapped_column()
    r2_key_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_hash: Mapped[str] = mapped_column(String(64))
    raw_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    media_links: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    source: Mapped[Source] = relationship(back_populates="raw_items")
    story: Mapped[Story | None] = relationship(back_populates="raw_item", uselist=False)


class Story(Base, TimestampMixin):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_item_id: Mapped[int] = mapped_column(ForeignKey("raw_items.id"))
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cleaned_text: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtopics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    timeline: Mapped[list] = mapped_column(JSONB, default=list)
    tension_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Confidence | None] = mapped_column(String(8), nullable=True)
    status: Mapped[StoryStatus] = mapped_column(String(16), default=StoryStatus.cleaned)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    raw_item: Mapped[RawItem] = relationship(back_populates="story")
    score: Mapped[StoryScore | None] = relationship(back_populates="story", uselist=False)
    candidate: Mapped[CandidateQueue | None] = relationship(back_populates="story", uselist=False)
    research_pack: Mapped[ResearchPack | None] = relationship(back_populates="story", uselist=False)
    scripts: Mapped[list[Script]] = relationship(back_populates="story")


class StoryScore(Base, TimestampMixin):
    __tablename__ = "story_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), unique=True)
    engagement: Mapped[float] = mapped_column(Float, default=0.0)
    freshness: Mapped[float] = mapped_column(Float, default=0.0)
    novelty: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_depth: Mapped[float] = mapped_column(Float, default=0.0)
    horror_fit: Mapped[float] = mapped_column(Float, default=0.0)
    reliability: Mapped[float] = mapped_column(Float, default=0.0)
    audience_match: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[Priority | None] = mapped_column(String(8), nullable=True)

    story: Mapped[Story] = relationship(back_populates="score")


class CandidateQueue(Base, TimestampMixin):
    __tablename__ = "candidate_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), unique=True)
    status: Mapped[StoryStatus] = mapped_column(String(16), default=StoryStatus.queued)
    priority: Mapped[Priority | None] = mapped_column(String(8), nullable=True)
    decision: Mapped[Decision] = mapped_column(String(20), default=Decision.pending)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sent_in_digest_at: Mapped[datetime | None] = mapped_column(nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    story: Mapped[Story] = relationship(back_populates="candidate")


class ResearchPack(Base, TimestampMixin):
    __tablename__ = "research_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), unique=True)
    core_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[list] = mapped_column(JSONB, default=list)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    proven: Mapped[list] = mapped_column(JSONB, default=list)
    speculative: Mapped[list] = mapped_column(JSONB, default=list)
    open_loops: Mapped[list] = mapped_column(JSONB, default=list)
    angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    drive_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    story: Mapped[Story] = relationship(back_populates="research_pack")


class Script(Base, TimestampMixin):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ScriptStatus] = mapped_column(String(16), default=ScriptStatus.draft)
    outline: Mapped[dict] = mapped_column(JSONB, default=dict)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    final: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_persona: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drive_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rewrite_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    story: Mapped[Story] = relationship(back_populates="scripts")


class VoiceProfile(Base, TimestampMixin):
    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    persona: Mapped[str] = mapped_column(String(64), unique=True)
    voice_card: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_files: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)


class Knowledge(Base, TimestampMixin):
    __tablename__ = "knowledge"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)


class VoiceExemplar(Base, TimestampMixin):
    __tablename__ = "voice_exemplars"

    id: Mapped[int] = mapped_column(primary_key=True)
    persona: Mapped[str] = mapped_column(String(64), index=True)
    source_file: Mapped[str] = mapped_column(String(300))
    segment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
