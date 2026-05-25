"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { compact, useApi } from "@/lib/use-api";
import { IconPlus, IconSpinner } from "@/components/icons";
import { ActiveJobs } from "@/components/active-jobs";
import { Empty, PageHeader, Skeleton } from "@/components/ui";

export default function YoutubePage() {
  const stats = useApi(() => api.youtubeStats(), []);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function ingest() {
    if (!url.trim()) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.ingestYoutube(url.trim());
      setMsg(r.msg || "Diproses di background.");
      setUrl("");
    } catch {
      setMsg("Gagal proses video.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="YouTube" sub="Statistik channel + kemas ulang" />

      <div className="px-5 pb-7">
        <label className="text-[11px] font-semibold uppercase tracking-widest text-faint">
          Kemas ulang video
        </label>
        <div className="mt-2 flex gap-2">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="URL atau judul video"
            className="h-11 flex-1 rounded-xl border border-line bg-surface px-3 text-sm text-fg outline-none placeholder:text-faint focus:border-accent"
          />
          <button
            onClick={ingest}
            disabled={busy}
            className="tap flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-fg disabled:opacity-60"
          >
            {busy ? <IconSpinner size={18} className="animate-spin" /> : <IconPlus size={18} />}
          </button>
        </div>
        {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
      </div>

      <ActiveJobs />

      <h2 className="px-5 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-widest text-faint">
        Channel dipantau
      </h2>
      {stats.loading ? (
        <div className="flex flex-col gap-3 px-5 pt-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : stats.data && stats.data.length > 0 ? (
        <div className="flex flex-col gap-3 px-5 pt-1">
          {stats.data.map((ch) => (
            <div key={ch.channel} className="card flex items-center gap-3 p-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {ch.thumbnail ? (
                <img src={ch.thumbnail} alt="" className="h-10 w-10 rounded-full" />
              ) : (
                <div className="h-10 w-10 rounded-full bg-surface" />
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-fg">{ch.title || ch.channel}</div>
                <div className="tnum text-xs text-faint">{compact(ch.videos)} video · {compact(ch.views)} views</div>
              </div>
              <div className="text-right">
                <div className="tnum text-base font-semibold text-fg">{compact(ch.subscribers)}</div>
                <div className="text-[10px] font-semibold uppercase tracking-widest text-faint">subs</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty>Belum ada channel. Tambah di tab Atur atau bilang ke bot.</Empty>
      )}
    </div>
  );
}
