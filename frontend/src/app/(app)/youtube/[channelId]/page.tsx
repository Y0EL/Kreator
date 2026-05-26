"use client";

import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { compact, useApi } from "@/lib/use-api";
import { IconChevron } from "@/components/icons";
import { LiteYouTube } from "@/components/lite-youtube";
import { Empty, Skeleton } from "@/components/ui";

export default function ChannelVideosPage() {
  const channelId = String(useParams().channelId);
  const router = useRouter();
  const { data, loading } = useApi(() => api.channelVideos(channelId), [channelId]);

  return (
    <div className="pb-6">
      <div className="flex items-center gap-1 px-3 pt-10 pb-2">
        <button onClick={() => router.back()} className="tap p-2 text-muted">
          <IconChevron size={20} className="rotate-180" />
        </button>
        <span className="text-xs text-faint">Video channel</span>
      </div>

      {loading ? (
        <div className="flex flex-col gap-4 px-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="aspect-video w-full" />
          ))}
        </div>
      ) : data && data.length > 0 ? (
        <div className="flex flex-col gap-5 px-5">
          {data.map((v) => (
            <div key={v.video_id}>
              <LiteYouTube id={v.video_id} title={v.title} thumbnail={v.thumbnail} />
              <div className="mt-2">
                <div className="line-clamp-2 text-sm font-medium leading-snug text-fg">{v.title}</div>
                <div className="tnum mt-0.5 text-xs text-faint">{compact(v.views)} views</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty>Ga ada video, atau channel ga ke-resolve.</Empty>
      )}
    </div>
  );
}
