"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { IconChevron } from "@/components/icons";
import { Empty, PageHeader, Skeleton } from "@/components/ui";

export default function ScriptsPage() {
  const { data, loading } = useApi(() => api.allScripts(), []);

  return (
    <div>
      <PageHeader title="Skrip" sub="Draft yang udah dibikin" />
      {loading ? (
        <div className="flex flex-col gap-px px-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : data && data.length > 0 ? (
        <div className="border-t border-line">
          {data.map((s) => (
            <Link
              key={s.story_id}
              href={`/scripts/${s.story_id}`}
              className="tap flex items-center gap-4 border-b border-line px-5 py-4 active:bg-surface"
            >
              <div className="min-w-0 flex-1">
                <h3 className="line-clamp-2 text-[15px] font-medium leading-snug text-fg">
                  {s.title || "Tanpa judul"}
                </h3>
                <div className="mt-1 flex items-center gap-1.5 text-xs text-faint">
                  <span className="tnum">v{s.version}</span>
                  {s.estimated_minutes != null && <span>· {s.estimated_minutes}m</span>}
                  {s.status && <span className="uppercase tracking-wide">· {s.status}</span>}
                </div>
              </div>
              <IconChevron size={16} className="text-faint" />
            </Link>
          ))}
        </div>
      ) : (
        <Empty>Belum ada draft. Approve kandidat dulu di tab Kandidat.</Empty>
      )}
    </div>
  );
}
