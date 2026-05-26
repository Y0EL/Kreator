import Link from "next/link";
import type { Candidate } from "@/lib/types";
import { IconChevron } from "./icons";
import { PriorityTag } from "./ui";

export function StoryCard({ c }: { c: Candidate }) {
  const n = Math.round(c.final_score * 100);
  const hot = n >= 70;
  return (
    <Link
      href={`/candidates/${c.id}`}
      className="tap card rise mx-5 mb-3 flex items-center gap-3 p-4"
    >
      <div
        className={`tnum flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg font-semibold ${
          hot ? "bg-accent-soft text-accent" : "bg-surface-2 text-fg"
        }`}
      >
        {n}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 className="line-clamp-2 text-[15px] font-medium leading-snug text-fg">
          {c.title || "Tanpa judul"}
        </h3>
        <div className="flex items-center gap-1.5 text-xs text-faint">
          <span className="truncate">{c.source || "?"}</span>
          {c.topic && (
            <>
              <span>·</span>
              <span className="uppercase tracking-wide">{c.topic}</span>
            </>
          )}
          {c.estimated_minutes != null && (
            <>
              <span>·</span>
              <span className="tnum">{c.estimated_minutes}m</span>
            </>
          )}
        </div>
        {c.viral_score != null && (
          <span className="tnum mt-0.5 inline-flex w-fit items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent">
            Potensi viral {c.viral_score}
            {c.viral_label ? ` · ${c.viral_label}` : ""}
          </span>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <PriorityTag priority={c.priority} />
        <IconChevron size={16} className="text-faint" />
      </div>
    </Link>
  );
}
