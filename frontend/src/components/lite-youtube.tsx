"use client";

import { useState } from "react";

const PIPED = (process.env.NEXT_PUBLIC_PIPED_INSTANCE || "https://piped.video").replace(/\/$/, "");

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
  const src = PIPED
    ? `${PIPED}/embed/${id}?autoplay=1`
    : `https://www.youtube-nocookie.com/embed/${id}?autoplay=1`;

  if (play) {
    return (
      <div>
        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
          <iframe
            className="absolute inset-0 h-full w-full"
            src={src}
            title={title || "video"}
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
        <a
          href={`https://www.youtube.com/watch?v=${id}`}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-block text-[11px] text-faint underline"
        >
          Ga jalan? buka di YouTube
        </a>
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
