"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { compact, useApi } from "@/lib/use-api";
import { IconChevron } from "@/components/icons";
import { LitePlaylist, LiteYouTube } from "@/components/lite-youtube";
import { Empty, Skeleton } from "@/components/ui";

export default function ChannelVideosPage() {
  const channelId = String(useParams().channelId);
  const router = useRouter();
  const [tab, setTab] = useState<"videos" | "playlists">("videos");
  const videos = useApi(() => api.channelVideos(channelId), [channelId]);
  const playlists = useApi(() => api.channelPlaylists(channelId), [channelId]);

  const cur = tab === "videos" ? videos : playlists;

  return (
    <div className="pb-6">
      <div className="flex items-center gap-1 px-3 pt-10 pb-2">
        <button onClick={() => router.back()} className="tap p-2 text-muted">
          <IconChevron size={20} className="rotate-180" />
        </button>
        <span className="text-xs text-faint">Channel</span>
      </div>

      <div className="flex gap-2 px-5 pb-3">
        {([
          ["videos", "Video"],
          ["playlists", "Playlist"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`tap rounded-full border px-4 py-1.5 text-xs font-medium ${
              tab === k ? "border-accent bg-accent-soft text-accent" : "border-line text-faint"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {cur.loading ? (
        <div className="flex flex-col gap-4 px-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="aspect-video w-full" />
          ))}
        </div>
      ) : tab === "videos" ? (
        videos.data && videos.data.length > 0 ? (
          <div className="flex flex-col gap-5 px-5">
            {videos.data.map((v) => (
              <div key={v.video_id}>
                <LiteYouTube id={v.video_id} title={v.title} thumbnail={v.thumbnail} />
                <div className="mt-2">
                  <div className="line-clamp-2 text-sm font-medium leading-snug text-fg">{v.title}</div>
                  {v.views > 0 && <div className="tnum mt-0.5 text-xs text-faint">{compact(v.views)} views</div>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty>Ga ada video, atau YouTube lagi nge-block server.</Empty>
        )
      ) : playlists.data && playlists.data.length > 0 ? (
        <div className="flex flex-col gap-5 px-5">
          {playlists.data.map((p) => (
            <div key={p.playlist_id}>
              <LitePlaylist id={p.playlist_id} title={p.title} thumbnail={p.thumbnail} count={p.count} />
              <div className="mt-2 line-clamp-2 text-sm font-medium leading-snug text-fg">{p.title}</div>
            </div>
          ))}
        </div>
      ) : (
        <Empty>Channel ini ga punya playlist publik.</Empty>
      )}
    </div>
  );
}
