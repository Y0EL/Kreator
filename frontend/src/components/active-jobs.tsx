"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { IconCheck, IconSpinner, IconX } from "@/components/icons";

const KIND_LABEL: Record<string, string> = {
  youtube: "Kemas ulang YouTube",
  draft: "Bikin draft skrip",
  crawl: "Crawl sumber",
  process: "Proses item",
  digest: "Kirim digest",
};

export function ActiveJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const dismissed = useRef<Set<string>>(new Set());

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      let anyRunning = false;
      try {
        const data = await api.jobs();
        if (alive) setJobs(data.filter((j) => !dismissed.current.has(j.id)));
        anyRunning = data.some((j) => j.status === "running");
      } catch {
        /* ignore */
      }
      timer = setTimeout(tick, anyRunning ? 1800 : 6000);
    }
    tick();

    return () => {
      alive = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function dismiss(id: string) {
    dismissed.current.add(id);
    setJobs((prev) => prev.filter((j) => j.id !== id));
    api.dismissJob(id).catch(() => {});
  }

  if (jobs.length === 0) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 z-30 px-4 bottom-[calc(5.25rem+env(safe-area-inset-bottom))]">
      <div className="pointer-events-auto mx-auto flex max-w-md flex-col gap-2">
        {jobs.slice(0, 3).map((j) => {
          const err = j.status === "error";
          return (
            <div
              key={j.id}
              className={`card rise p-3.5 ${err ? "border-accent bg-accent-soft" : ""}`}
            >
            <div className="flex items-center gap-2">
              {j.status === "running" ? (
                <IconSpinner size={15} className="animate-spin text-accent" />
              ) : err ? (
                <IconX size={15} className="text-accent" />
              ) : (
                <IconCheck size={15} className="text-accent" />
              )}
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-fg">
                {j.title || KIND_LABEL[j.kind] || "Proses"}
              </span>
              <span className={`tnum text-sm font-semibold ${err ? "text-accent" : "text-fg"}`}>
                {err ? "Gagal" : `${j.percent}%`}
              </span>
              <button
                onClick={() => dismiss(j.id)}
                aria-label="Tutup notifikasi"
                className="tap -my-1 -mr-1 flex h-7 w-7 items-center justify-center rounded-lg text-faint active:bg-surface-2"
              >
                <IconX size={14} />
              </button>
            </div>

            {!err && (
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
                  style={{ width: `${Math.min(100, Math.max(3, j.percent))}%` }}
                />
              </div>
            )}

              <div className={`mt-2 text-xs ${err ? "font-medium text-accent" : "text-muted"}`}>
                {err ? j.error || "Gagal diproses" : j.stage}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
