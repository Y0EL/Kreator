"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { StoryCard } from "@/components/story-card";
import { SystemStatus } from "@/components/system-status";
import { Empty, PageHeader, Skeleton, StatBlock } from "@/components/ui";
import { IconActivity, IconSend, IconStack } from "@/components/icons";

const today = new Date().toLocaleDateString("id-ID", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

function QuickAction({
  label,
  Icon,
  busy,
  onClick,
}: {
  label: string;
  Icon: (p: { size?: number; className?: string }) => React.ReactNode;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="tap flex flex-1 items-center justify-center gap-2 rounded-xl border border-line py-3 text-xs font-medium text-fg active:bg-surface disabled:text-faint"
    >
      <Icon size={15} className={busy ? "text-accent" : "text-muted"} />
      {busy ? "..." : label}
    </button>
  );
}

export default function HomePage() {
  const stats = useApi(() => api.stats(), []);
  const cands = useApi(() => api.candidates(), []);
  const [busy, setBusy] = useState<string | null>(null);

  async function trigger(name: string) {
    setBusy(name);
    try {
      await api.action(name);
    } catch {
      /* ignore */
    } finally {
      setTimeout(() => setBusy(null), 1500);
    }
  }

  const top = (cands.data || []).slice(0, 6);

  return (
    <div>
      <PageHeader title="Yoel" sub={today} />

      <div className="card mx-5 grid grid-cols-3 overflow-hidden rounded-2xl">
        <div className="px-4 py-4">
          <StatBlock label="Kandidat" value={stats.data?.candidates ?? "·"} />
        </div>
        <div className="border-l border-line px-4 py-4">
          <StatBlock label="Sumber" value={stats.data?.sources_active ?? "·"} />
        </div>
        <div className="border-l border-line px-4 py-4">
          <StatBlock label="Skrip" value={stats.data?.scripts ?? "·"} />
        </div>
      </div>

      <SystemStatus />

      <div className="flex gap-2 px-5 pt-4">
        <QuickAction label="Crawl" Icon={IconActivity} busy={busy === "crawl"} onClick={() => trigger("crawl")} />
        <QuickAction label="Proses" Icon={IconStack} busy={busy === "process"} onClick={() => trigger("process")} />
        <QuickAction label="Digest" Icon={IconSend} busy={busy === "digest"} onClick={() => trigger("digest")} />
      </div>

      <h2 className="px-5 pt-8 pb-1 text-[11px] font-semibold uppercase tracking-widest text-faint">
        Kandidat teratas
      </h2>

      {cands.loading ? (
        <div className="flex flex-col gap-3 px-5 pt-1">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[76px]" />
          ))}
        </div>
      ) : top.length === 0 ? (
        <Empty>Belum ada kandidat. Jalanin Crawl + Proses dulu.</Empty>
      ) : (
        <div>
          {top.map((c) => (
            <StoryCard key={c.id} c={c} />
          ))}
        </div>
      )}
    </div>
  );
}
