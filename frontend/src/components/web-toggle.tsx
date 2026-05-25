"use client";

export function WebSearchToggle({
  on,
  set,
  className = "",
}: {
  on: boolean;
  set: (v: boolean) => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => set(!on)}
      aria-pressed={on}
      className={`tap flex items-center gap-2 text-xs font-medium ${on ? "text-accent" : "text-muted"} ${className}`}
    >
      <span
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${
          on ? "bg-accent" : "bg-surface-2"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-fg transition-all duration-200 ${
            on ? "left-[1.125rem]" : "left-0.5"
          }`}
        />
      </span>
      Web search
    </button>
  );
}
