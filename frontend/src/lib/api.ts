import type {
  Candidate,
  Job,
  ScriptItem,
  System,
  ScriptListItem,
  SourceItem,
  Stats,
  StoryDetail,
  YtStat,
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
  jobs: () => req<Job[]>("/api/jobs"),
  dismissJob: (id: string) => req<{ ok: boolean }>(`/api/jobs/${id}`, { method: "DELETE" }),
  system: () => req<System>("/api/system"),
};
