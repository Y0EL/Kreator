"use client";

import { useEffect, useId, useState } from "react";

// Hanya satu player yang boleh aktif. Saat satu diputar, yang lain berhenti.
let _active: string | null = null;
const _subs = new Set<() => void>();
function activate(key: string) {
  _active = key;
  _subs.forEach((f) => f());
}

function useSinglePlayer(key: string, stop: () => void) {
  useEffect(() => {
    const f = () => {
      if (_active !== key) stop();
    };
    _subs.add(f);
    return () => {
      _subs.delete(f);
      if (_active === key) _active = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}

function useLandscapeOnFullscreen() {
  useEffect(() => {
    const o = screen.orientation as ScreenOrientation & {
      lock?: (orientation: string) => Promise<void>;
      unlock?: () => void;
    };
    function onFs() {
      if (!o || !o.lock) return;
      if (document.fullscreenElement) o.lock("landscape").catch(() => {});
      else o.unlock?.();
    }
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-label="Tutup pemutar"
      className="tap absolute right-2 top-2 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-black/70 text-white active:bg-black"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
        <path d="M6 6l12 12M18 6 6 18" />
      </svg>
    </button>
  );
}

export function LiteYouTube({
  id,
  title,
  thumbnail,
}: {
  id: string;
  title?: string | null;
  thumbnail?: string | null;
}) {
  const key = useId();
  const [play, setPlay] = useState(false);
  useSinglePlayer(key, () => setPlay(false));
  useLandscapeOnFullscreen();
  const thumb = thumbnail || `https://i.ytimg.com/vi/${id}/mqdefault.jpg`;

  if (play) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&playsinline=1`}
          title={title || "video"}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
        <CloseButton onClick={() => setPlay(false)} />
      </div>
    );
  }

  return (
    <button
      onClick={() => {
        activate(key);
        setPlay(true);
      }}
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

export function LitePlaylist({
  id,
  title,
  thumbnail,
  count,
}: {
  id: string;
  title?: string | null;
  thumbnail?: string | null;
  count?: number;
}) {
  const key = useId();
  const [play, setPlay] = useState(false);
  useSinglePlayer(key, () => setPlay(false));
  useLandscapeOnFullscreen();

  if (play) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/videoseries?list=${id}&autoplay=1&playsinline=1`}
          title={title || "playlist"}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
        <CloseButton onClick={() => setPlay(false)} />
      </div>
    );
  }

  return (
    <button
      onClick={() => {
        activate(key);
        setPlay(true);
      }}
      className="tap relative aspect-video w-full overflow-hidden rounded-xl bg-surface-2"
      aria-label={`Putar playlist ${title || ""}`}
    >
      {thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={thumbnail} alt={title || ""} className="h-full w-full object-cover" loading="lazy" />
      ) : (
        <div className="h-full w-full bg-surface-2" />
      )}
      <span className="absolute inset-0 flex items-center justify-center bg-black/35">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-black/65">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff" aria-hidden="true">
            <path d="M8 5v14l11-7z" />
          </svg>
        </span>
      </span>
      {count ? (
        <span className="absolute bottom-2 right-2 rounded-md bg-black/75 px-2 py-0.5 text-[11px] font-semibold text-white">
          {count} video
        </span>
      ) : null}
    </button>
  );
}
