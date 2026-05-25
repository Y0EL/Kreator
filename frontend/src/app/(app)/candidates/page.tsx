"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { StoryCard } from "@/components/story-card";
import { Empty, PageHeader, Skeleton } from "@/components/ui";

const FILTERS = [
  { k: "", l: "Semua" },
  { k: "A", l: "Prioritas A" },
  { k: "B", l: "Prioritas B" },
];

export default function CandidatesPage() {
  const [pri, setPri] = useState("");
  const { data, loading } = useApi(() => api.candidates(pri || undefined), [pri]);

  return (
    <div>
      <PageHeader title="Kandidat" sub="Cerita yang lolos skor" />
      <div className="flex gap-2 px-5 pb-3">
        {FILTERS.map((f) => (
          <button
            key={f.k}
            onClick={() => setPri(f.k)}
            className={`tap rounded-full border px-3.5 py-1.5 text-xs font-medium ${
              pri === f.k ? "border-accent bg-accent-soft text-accent" : "border-line text-faint"
            }`}
          >
            {f.l}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="flex flex-col gap-3 px-5 pt-1">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-[76px]" />
          ))}
        </div>
      ) : data && data.length > 0 ? (
        <div className="pt-1">
          {data.map((c) => (
            <StoryCard key={c.id} c={c} />
          ))}
        </div>
      ) : (
        <Empty>Ga ada kandidat di filter ini.</Empty>
      )}
    </div>
  );
}
