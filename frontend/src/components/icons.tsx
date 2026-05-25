type P = { className?: string; size?: number };

function S({ className, size = 22, children }: P & { children: React.ReactNode }) {
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
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const IconHome = (p: P) => (
  <S {...p}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></S>
);
export const IconStack = (p: P) => (
  <S {...p}><path d="M12 3 3 8l9 5 9-5-9-5Z" /><path d="m3 13 9 5 9-5" /></S>
);
export const IconScript = (p: P) => (
  <S {...p}><path d="M6 3h9l4 4v14H6z" /><path d="M14 3v5h5" /><path d="M9 13h7M9 17h5" /></S>
);
export const IconPlay = (p: P) => (
  <S {...p}><rect x="3" y="5" width="18" height="14" rx="3" /><path d="m11 9 4 3-4 3z" fill="currentColor" /></S>
);
export const IconSliders = (p: P) => (
  <S {...p}><path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h12M20 18h0" /><circle cx="16" cy="6" r="2" /><circle cx="8" cy="12" r="2" /><circle cx="18" cy="18" r="2" /></S>
);
export const IconCheck = (p: P) => (<S {...p}><path d="m5 12 5 5L20 6" /></S>);
export const IconX = (p: P) => (<S {...p}><path d="M6 6l12 12M18 6 6 18" /></S>);
export const IconClock = (p: P) => (<S {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></S>);
export const IconSearch = (p: P) => (<S {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></S>);
export const IconPlus = (p: P) => (<S {...p}><path d="M12 5v14M5 12h14" /></S>);
export const IconRefresh = (p: P) => (
  <S {...p}><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 4v5h-5" /></S>
);
export const IconTrash = (p: P) => (
  <S {...p}><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" /></S>
);
export const IconChevron = (p: P) => (<S {...p}><path d="m9 6 6 6-6 6" /></S>);
export const IconExternal = (p: P) => (
  <S {...p}><path d="M14 4h6v6" /><path d="M20 4 10 14" /><path d="M19 14v5H5V5h5" /></S>
);
export const IconPower = (p: P) => (<S {...p}><path d="M12 3v8" /><path d="M6.5 7a8 8 0 1 0 11 0" /></S>);
export const IconActivity = (p: P) => (<S {...p}><path d="M3 12h4l3 7 4-14 3 7h4" /></S>);
export const IconSend = (p: P) => (<S {...p}><path d="M22 3 11 14" /><path d="M22 3 15 21l-4-7-7-4z" /></S>);
export const IconLogout = (p: P) => (
  <S {...p}><path d="M9 21H5V3h4" /><path d="M16 16l4-4-4-4" /><path d="M20 12H9" /></S>
);
export const IconSun = (p: P) => (
  <S {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19" /></S>
);
export const IconMoon = (p: P) => (
  <S {...p}><path d="M21 12.8A8 8 0 1 1 11.2 3a6 6 0 0 0 9.8 9.8Z" /></S>
);
export const IconSpinner = (p: P) => (
  <S {...p}><path d="M12 3a9 9 0 1 0 9 9" /></S>
);
