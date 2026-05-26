export function PlatformIcon({ platform, size = 20 }: { platform: string; size?: number }) {
  if (platform === "youtube")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
        <rect x="1" y="4" width="22" height="16" rx="5" fill="#FF0000" />
        <path d="M10 8.3v7.4l6.2-3.7z" fill="#fff" />
      </svg>
    );
  if (platform === "wikipedia")
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18" />
      </svg>
    );
  if (platform === "rss")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <circle cx="6" cy="18" r="2.2" />
        <path d="M4 10.5a9.5 9.5 0 0 1 9.5 9.5h-3A6.5 6.5 0 0 0 4 13.5z" />
        <path d="M4 4a16 16 0 0 1 16 16h-3A13 13 0 0 0 4 7z" />
      </svg>
    );
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 20h16" />
      <path d="M6 16l9-9 3 3-9 9H6z" />
    </svg>
  );
}
