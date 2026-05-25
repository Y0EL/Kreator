from __future__ import annotations

import enum


class SourceType(str, enum.Enum):
    forum = "forum"
    reddit = "reddit"
    blog_archive = "blog_archive"
    rss = "rss"
    media = "media"
    submission = "submission"
    mediawiki = "mediawiki"
    search = "search"


class SourceStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    disabled = "disabled"


class CrawlJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class StoryStatus(str, enum.Enum):
    crawled = "crawled"
    cleaned = "cleaned"
    unique = "unique"
    scored = "scored"
    queued = "queued"
    approved = "approved"
    researching = "researching"
    outline = "outline"
    draft = "draft"
    edit = "edit"
    audio = "audio"
    video = "video"
    scheduled = "scheduled"
    published = "published"
    analyzed = "analyzed"
    duplicate = "duplicate"


class Confidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Priority(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    reject = "reject"


class Decision(str, enum.Enum):
    pending = "pending"
    approve = "approve"
    reject = "reject"
    later = "later"
    deep_research = "deep_research"
    request_rewrite = "request_rewrite"


class ScriptStatus(str, enum.Enum):
    outline = "outline"
    draft = "draft"
    revised = "revised"
    final = "final"
