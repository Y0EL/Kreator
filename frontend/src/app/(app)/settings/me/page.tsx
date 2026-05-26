"use client";

import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { compact, useApi } from "@/lib/use-api";
import { IconChevron } from "@/components/icons";
import { LiteYouTube } from "@/components/lite-youtube";
import { MiniChart } from "@/components/mini-chart";
import { Skeleton, StatBlock } from "@/components/ui";

export default function MePage() {
  const router = useRouter();
  const me = useApi(() => api.youtubeMe(), []);
  const hist = useApi(() => api.youtubeMeHistory(90), []);

  const ch = me.data?.channel;
  const points = hist.data || [];
  const subsSeries = points.map((p) => p.subscribers);
  const viewsSeries = points.map((p) => p.views);
  const subsDelta = points.length >= 2 ? points[points.length - 1].subscribers - points[0].subscribers : 0;
  const viewsDelta = points.length >= 2 ? points[points.length - 1].views - points[0].views : 0;

  return (
    <div className="pb-8">
      <div className="flex items-center gap-1 px-3 pt-10 pb-2">
        <button onClick={() => router.back()} className="tap p-2 text-muted">
          <IconChevron size={20} className="rotate-180" />
        </button>
        <span className="text-xs text-faint">Statistik channel</span>
      </div>

      {me.loading ? (
        <div className="px-5">
          <Skeleton className="h-24" />
          <Skeleton className="mt-4 h-40" />
        </div>
      ) : (
        <div className="px-5">
          <div className="flex items-center gap-3">
            {ch?.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={ch.thumbnail} alt="" className="h-14 w-14 rounded-full" />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-base font-bold text-accent">
                YL
              </div>
            )}
            <div className="min-w-0">
              <div className="truncate text-lg font-bold leading-tight text-fg">
                {ch?.title || "@yoelmanoppo"}
              </div>
              {!ch && <div className="text-xs text-faint">Set YOUTUBE_API_KEY + owner handle buat lihat statistik.</div>}
            </div>
          </div>

          <div className="card mt-4 grid grid-cols-3 overflow-hidden rounded-2xl">
            <div className="px-4 py-4">
              <StatBlock label="Subscriber" value={ch ? compact(ch.subscribers) : "·"} />
            </div>
            <div className="border-l border-line px-4 py-4">
              <StatBlock label="Total views" value={ch ? compact(ch.views) : "·"} />
            </div>
            <div className="border-l border-line px-4 py-4">
              <StatBlock label="Video" value={ch ? compact(ch.videos) : "·"} />
            </div>
          </div>

          <div className="card mt-4 rounded-2xl p-4">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-faint">Subscriber</span>
              <span className="tnum text-xs font-semibold text-accent">
                {subsDelta >= 0 ? "+" : ""}
                {compact(subsDelta)} / {points.length}h
              </span>
            </div>
            <div className="mt-3">
              <MiniChart points={subsSeries} />
            </div>
          </div>

          <div className="card mt-4 rounded-2xl p-4">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-faint">Views</span>
              <span className="tnum text-xs font-semibold text-accent">
                {viewsDelta >= 0 ? "+" : ""}
                {compact(viewsDelta)} / {points.length}h
              </span>
            </div>
            <div className="mt-3">
              <MiniChart points={viewsSeries} />
            </div>
          </div>

          {me.data?.videos && me.data.videos.length > 0 && (
            <>
              <h2 className="px-1 pb-2 pt-6 text-[11px] font-semibold uppercase tracking-widest text-faint">
                Video terbaru
              </h2>
              <div className="flex flex-col gap-5">
                {me.data.videos.map((v) => (
                  <div key={v.video_id}>
                    <LiteYouTube id={v.video_id} title={v.title} thumbnail={v.thumbnail} />
                    <div className="mt-2">
                      <div className="line-clamp-2 text-sm font-medium leading-snug text-fg">{v.title}</div>
                      <div className="tnum mt-0.5 text-xs text-faint">{compact(v.views)} views</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
