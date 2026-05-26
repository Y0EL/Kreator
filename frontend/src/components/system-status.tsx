"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { System } from "@/lib/types";
import { IconClock } from "@/components/icons";

function fmtTime(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("id-ID", {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "-";
  }
}

const JOB_LABEL: Record<string, string> = {
  collection: "Crawl berikutnya",
  stats_snapshot: "Catat statistik channel",
};

export function SystemStatus() {
  const [sys, setSys] = useState<System | null>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function tick() {
      try {
        const data = await api.system();
        if (alive) setSys(data);
      } catch {
        /* ignore */
      }
      timer = setTimeout(tick, 30000);
    }
    tick();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, []);

  if (!sys) return null;
  const running = sys.scheduler_running;

  return (
    <div className="card mx-5 mt-4 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {running && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
            )}
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                running ? "bg-accent" : "bg-faint"
              }`}
            />
          </span>
          <span className="text-sm font-medium text-fg">
            {running ? "Scheduler aktif" : "Scheduler mati"}
          </span>
        </div>
        <span className="rounded-lg bg-surface-2 px-2.5 py-1 text-xs font-medium text-muted">
          {sys.mode}
        </span>
      </div>

      <div className="mt-3 flex flex-col gap-1.5">
        {sys.jobs.map((j) => (
          <div key={j.id} className="flex items-center gap-2 text-xs text-muted">
            <IconClock size={13} className="text-faint" />
            <span className="flex-1">{JOB_LABEL[j.id] || j.id}</span>
            <span className="tnum text-fg">{fmtTime(j.next_run)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
