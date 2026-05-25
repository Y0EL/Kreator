import type { ScoreBreakdown } from "@/lib/types";

export function PriorityTag({ priority }: { priority: string | null }) {
  if (!priority) return null;
  const base =
    "inline-flex h-7 min-w-7 items-center justify-center rounded-lg px-2 text-xs font-bold tnum";
  if (priority === "A") return <span className={`${base} bg-accent text-accent-fg`}>A</span>;
  if (priority === "B") return <span className={`${base} bg-surface-2 text-fg`}>B</span>;
  return <span className={`${base} bg-surface-2 text-faint`}>{priority}</span>;
}

export function ConfidenceTag({ confidence }: { confidence: string | null }) {
  if (!confidence) return null;
  const label = confidence.toUpperCase().slice(0, 3);
  return <span className="text-[10px] font-semibold uppercase tracking-widest text-faint">{label}</span>;
}

export function Score({ value, big = false }: { value: number; big?: boolean }) {
  const n = Math.round(value * 100);
  const hot = n >= 70;
  return (
    <span className={`tnum font-semibold ${big ? "text-3xl" : "text-lg"} ${hot ? "text-accent" : "text-fg"}`}>
      {n}
    </span>
  );
}

const SCORE_LABELS: Record<keyof Omit<ScoreBreakdown, "final_score" | "priority">, string> = {
  engagement: "Engagement",
  freshness: "Freshness",
  novelty: "Novelty",
  narrative_depth: "Narrative",
  horror_fit: "Horror fit",
  reliability: "Reliability",
  audience_match: "Audience",
};

export function ScoreBars({ score }: { score: ScoreBreakdown }) {
  const keys = Object.keys(SCORE_LABELS) as (keyof typeof SCORE_LABELS)[];
  return (
    <div className="flex flex-col gap-3">
      {keys.map((k) => {
        const v = Math.max(0, Math.min(1, score[k] as number));
        const pct = Math.round(v * 100);
        const hot = pct >= 70;
        return (
          <div key={k} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-xs text-muted">{SCORE_LABELS[k]}</span>
            <div className="h-px flex-1 bg-line relative">
              <div
                className={`absolute -top-px h-[3px] ${hot ? "bg-accent" : "bg-fg"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="tnum w-8 shrink-0 text-right text-xs text-faint">{pct}</span>
          </div>
        );
      })}
    </div>
  );
}

export function StatBlock({ label, value }: { label: string; value: string | number; }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-faint">{label}</span>
      <span className="tnum text-3xl font-semibold text-fg">{value}</span>
    </div>
  );
}

export function PageHeader({ title, sub, right }: { title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <header className="flex items-end justify-between gap-3 px-5 pt-12 pb-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-fg">{title}</h1>
        {sub && <p className="mt-0.5 text-sm text-muted">{sub}</p>}
      </div>
      {right}
    </header>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-2xl ${className}`} />;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-20 text-center">
      <p className="text-sm text-faint">{children}</p>
    </div>
  );
}
