import type {
  Candidate,
  Job,
  OwnChannel,
  ScriptItem,
  StatPoint,
  System,
  ScriptListItem,
  SourceItem,
  Stats,
  StoryDetail,
  YtChannel,
  YtStat,
  YtVideo,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "https://konten-yoel.fly.dev";
const TOKEN_KEY = "yoel_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

const _cache = new Map<string, { v: unknown; exp: number }>();

async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = _cache.get(key);
  if (hit && hit.exp > Date.now()) return hit.v as T;
  const v = await fn();
  _cache.set(key, { v, exp: Date.now() + ttlMs });
  return v;
}

function bustCache(prefix: string): void {
  for (const k of [..._cache.keys()]) if (k.startsWith(prefix)) _cache.delete(k);
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(BASE + path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("json") ? res.json() : res.text()) as Promise<T>;
}

export const api = {
  stats: () => req<Stats>("/api/stats"),
  candidates: (priority?: string) =>
    req<Candidate[]>(`/api/candidates${priority ? `?priority=${priority}` : ""}`),
  story: (id: number) => req<StoryDetail>(`/api/stories/${id}`),
  allScripts: () => req<ScriptListItem[]>("/api/scripts"),
  scripts: (id: number) => req<ScriptItem[]>(`/api/stories/${id}/scripts`),
  decide: (id: number, action: string, webSearch = false) =>
    req<{ ok: boolean }>(`/api/stories/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ action, web_search: webSearch }),
    }),
  regenerate: (id: number, note?: string, webSearch = false) =>
    req<{ ok: boolean }>(`/api/stories/${id}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ note, web_search: webSearch }),
    }),
  sources: () => req<SourceItem[]>("/api/sources"),
  addSource: (body: { name: string; type: string; feed_url?: string; channels?: string[] }) =>
    req<{ id: number }>("/api/sources", { method: "POST", body: JSON.stringify(body) }),
  patchSource: (id: number, body: { status?: string }) =>
    req<{ ok: boolean }>(`/api/sources/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteSource: (id: number) => req<{ ok: boolean }>(`/api/sources/${id}`, { method: "DELETE" }),
  ingestYoutube: (video: string, webSearch = false) =>
    req<{ ok: boolean; msg: string }>("/api/ingest/youtube", {
      method: "POST",
      body: JSON.stringify({ video, web_search: webSearch }),
    }),
  action: (name: string) => req<{ ok: boolean }>(`/api/actions/${name}`, { method: "POST" }),
  youtubeStats: () => req<YtStat[]>("/api/youtube/stats"),
  youtubeChannels: () =>
    cached("yt:channels", 300_000, () => req<YtChannel[]>("/api/youtube/channels")),
  addChannel: async (channel: string) => {
    const r = await req<{ added: boolean; total: number }>("/api/youtube/channels", {
      method: "POST",
      body: JSON.stringify({ channel }),
    });
    bustCache("yt:");
    return r;
  },
  removeChannel: async (channel: string) => {
    const r = await req<{ removed: boolean; total: number }>(
      `/api/youtube/channels?channel=${encodeURIComponent(channel)}`,
      { method: "DELETE" },
    );
    bustCache("yt:");
    return r;
  },
  channelVideos: (channelId: string, limit = 12) =>
    cached(`yt:videos:${channelId}:${limit}`, 600_000, () =>
      req<YtVideo[]>(`/api/youtube/channel/${encodeURIComponent(channelId)}/videos?limit=${limit}`),
    ),
  bulkDeleteSources: (ids: number[]) =>
    req<{ ok: boolean; deleted: number }>("/api/sources/bulk_delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  youtubeMe: () => cached("yt:me", 300_000, () => req<OwnChannel>("/api/youtube/me")),
  youtubeMeHistory: (days = 90) =>
    cached(`yt:hist:${days}`, 300_000, () =>
      req<StatPoint[]>(`/api/youtube/me/history?days=${days}`),
    ),
  jobs: () => req<Job[]>("/api/jobs"),
  dismissJob: (id: string) => req<{ ok: boolean }>(`/api/jobs/${id}`, { method: "DELETE" }),
  system: () => req<System>("/api/system"),
};
