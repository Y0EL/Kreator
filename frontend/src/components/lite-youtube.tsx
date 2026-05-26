"use client";

import { useState } from "react";

export function LiteYouTube({
  id,
  title,
  thumbnail,
}: {
  id: string;
  title?: string | null;
  thumbnail?: string | null;
}) {
  const [play, setPlay] = useState(false);
  const thumb = thumbnail || `https://i.ytimg.com/vi/${id}/mqdefault.jpg`;

  if (play) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1`}
          title={title || "video"}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <button
      onClick={() => setPlay(true)}
      className="tap relative aspect-video w-full overflow-hidden rounded-xl bg-surface-2"
      aria-label={`Putar ${title || "video"}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={thumb} alt={title || ""} className="h-full w-full object-cover" loading="lazy" />
      <span className="absolute inset-0 flex items-center justify-center bg-black/10">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-black/65">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff" aria-hidden="true">
            <path d="M8 5v14l11-7z" />
          </svg>
        </span>
      </span>
    </button>
  );
}
