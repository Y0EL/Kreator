export type Stats = {
  sources: number;
  sources_active: number;
  raw_items: number;
  stories: number;
  candidates: number;
  scripts: number;
};

export type Candidate = {
  id: number;
  title: string | null;
  summary: string | null;
  topic: string | null;
  confidence: string | null;
  estimated_minutes: number | null;
  final_score: number;
  priority: string | null;
  source: string | null;
  source_url: string | null;
  viral_score: number | null;
  viral_label: string | null;
  viral_reasons: string[];
  where_from: string | null;
};

export type Pitch = {
  viral_score: number;
  viral_label: string | null;
  hook: string | null;
  reasons: string[];
  where_from: string | null;
};

export type ScoreBreakdown = {
  engagement: number;
  freshness: number;
  novelty: number;
  narrative_depth: number;
  horror_fit: number;
  reliability: number;
  audience_match: number;
  final_score: number;
  priority: string | null;
};

export type ResearchPack = {
  core_summary: string | null;
  timeline: string[];
  sources: unknown[];
  proven: string[];
  speculative: string[];
  open_loops: string[];
  angle: string | null;
  confidence_notes: string | null;
};

export type StoryDetail = {
  id: number;
  title: string | null;
  summary: string | null;
  topic: string | null;
  subtopics: string[];
  entities: Record<string, string[]>;
  timeline: string[];
  confidence: string | null;
  estimated_minutes: number | null;
  status: string | null;
  excerpt: string | null;
  source_url: string | null;
  posted_at: string | null;
  score: ScoreBreakdown | null;
  pitch: Pitch | null;
  research_pack: ResearchPack | null;
  scripts: { id: number; version: number; status: string | null; drive_url: string | null }[];
};

export type ScriptItem = {
  id: number;
  version: number;
  status: string | null;
  draft: string | null;
  drive_url: string | null;
  rewrite_note: string | null;
  estimated_minutes: number | null;
  voice_persona: string | null;
};

export type ScriptListItem = {
  id: number;
  story_id: number;
  version: number;
  status: string | null;
  drive_url: string | null;
  estimated_minutes: number | null;
  title: string | null;
};

export type SourceItem = {
  id: number;
  name: string;
  type: string;
  status: string;
  base_url: string;
  priority: number;
  consecutive_errors: number;
  last_crawled_at: string | null;
  parser_config: Record<string, unknown>;
};

export type Job = {
  id: string;
  kind: string;
  title: string | null;
  stage: string;
  percent: number;
  status: "running" | "done" | "error";
  error: string | null;
  story_id: number | null;
  created_at: number;
  updated_at: number;
};

export type System = {
  scheduler_running: boolean;
  mode: string;
  tz: string;
  now: string;
  jobs: { id: string; next_run: string | null }[];
};

export type YtStat = {
  channel: string;
  title: string | null;
  thumbnail: string | null;
  subscribers: number;
  views: number;
  videos: number;
};

export type YtChannel = {
  channel: string;
  channel_id: string | null;
  title: string | null;
  thumbnail: string | null;
  subscribers: number;
  views: number;
  videos: number;
};

export type YtVideo = {
  video_id: string;
  title: string | null;
  thumbnail: string | null;
  views: number;
  published_at: string | null;
};

export type OwnChannel = {
  channel: YtChannel | null;
  videos: YtVideo[];
};

export type StatPoint = {
  date: string;
  subscribers: number;
  views: number;
  videos: number;
};
