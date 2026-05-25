"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { IconChevron, IconRefresh } from "@/components/icons";
import { ActiveJobs } from "@/components/active-jobs";
import { WebSearchToggle } from "@/components/web-toggle";
import { Skeleton } from "@/components/ui";

export default function ReaderPage() {
  const id = Number(useParams().id);
  const router = useRouter();
  const { data, loading } = useApi(() => api.scripts(id), [id]);
  const [v, setV] = useState(0);
  const [regen, setRegen] = useState(false);
  const [web, setWeb] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const scripts = data || [];
  const cur = scripts[v];

  async function doRegen() {
    setRegen(true);
    setMsg(null);
    try {
      await api.regenerate(id, undefined, web);
      setMsg("Lagi nulis ulang. Versi baru nyusul ke grup Telegram, refresh bentar lagi.");
    } catch {
      setMsg("Gagal regenerate.");
    } finally {
      setTimeout(() => setRegen(false), 1500);
    }
  }

  if (loading)
    return (
      <div className="px-5 pt-12">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="mt-4 h-80" />
      </div>
    );

  return (
    <div>
      <div className="flex items-center gap-1 px-3 pt-10 pb-2">
        <button onClick={() => router.back()} className="tap p-2 text-muted">
          <IconChevron size={20} className="rotate-180" />
        </button>
        <span className="text-xs text-faint">Skrip · story #{id}</span>
        <button
          onClick={doRegen}
          disabled={regen}
          className="tap ml-auto flex items-center gap-1.5 border border-line px-3 py-1.5 text-xs text-fg active:bg-surface"
        >
          <IconRefresh size={14} className={regen ? "animate-spin text-accent" : "text-muted"} />
          Regenerate
        </button>
      </div>

      <div className="flex justify-end px-5 pb-1">
        <WebSearchToggle on={web} set={setWeb} />
      </div>

      <ActiveJobs />

      {scripts.length > 1 && (
        <div className="flex gap-2 px-5 pb-3">
          {scripts.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setV(i)}
              className={`tap border px-3 py-1 text-xs tnum ${
                i === v ? "border-accent text-accent" : "border-line text-faint"
              }`}
            >
              v{s.version}
            </button>
          ))}
        </div>
      )}

      {msg && <p className="mx-5 mb-3 border border-accent-dim bg-surface px-3 py-2 text-xs text-fg">{msg}</p>}

      {cur ? (
        <article className="whitespace-pre-wrap border-t border-line px-5 py-5 text-[15px] leading-relaxed text-fg">
          {cur.draft || "(draft kosong)"}
        </article>
      ) : (
        <p className="px-5 py-10 text-center text-sm text-faint">Belum ada draft.</p>
      )}

      <p className="px-5 pb-6 text-xs text-faint">File DOCX & PDF lengkap dikirim ke grup Telegram.</p>
    </div>
  );
}
