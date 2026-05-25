"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import {
  IconCheck,
  IconChevron,
  IconClock,
  IconExternal,
  IconSearch,
  IconX,
} from "@/components/icons";
import { ConfidenceTag, PriorityTag, Score, ScoreBars, Skeleton } from "@/components/ui";
import { WebSearchToggle } from "@/components/web-toggle";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line px-5 py-5">
      <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-faint">{title}</h2>
      {children}
    </section>
  );
}

function Bullets({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-sm text-faint">-</p>;
  return (
    <ul className="flex flex-col gap-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-fg">
          <span className="mt-2 h-1 w-1 shrink-0 bg-accent" />
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

export default function StoryPage() {
  const params = useParams();
  const id = Number(params.id);
  const router = useRouter();
  const { data: s, loading } = useApi(() => api.story(id), [id]);
  const [acting, setActing] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [web, setWeb] = useState(false);

  async function decide(action: string) {
    setActing(action);
    try {
      await api.decide(id, action, web);
      setDone(action);
    } catch {
      /* ignore */
    } finally {
      setActing(null);
    }
  }

  if (loading)
    return (
      <div className="px-5 pt-12">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="mt-4 h-40" />
      </div>
    );
  if (!s) return <div className="px-5 pt-12 text-faint">Cerita ga ketemu.</div>;

  const entities = Object.entries(s.entities || {}).filter(([, v]) => Array.isArray(v) && v.length);

  return (
    <div>
      <div className="flex items-center gap-1 px-3 pt-10 pb-1">
        <button onClick={() => router.back()} className="tap p-2 text-muted">
          <IconChevron size={20} className="rotate-180" />
        </button>
        <span className="text-xs text-faint">Kandidat #{s.id}</span>
      </div>

      <div className="px-5 pt-2">
        <h1 className="text-2xl font-bold leading-tight tracking-tight text-fg">
          {s.title || "Tanpa judul"}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-faint">
          {s.topic && <span className="uppercase tracking-wide">{s.topic}</span>}
          {s.estimated_minutes != null && <span>· {s.estimated_minutes} menit</span>}
          <ConfidenceTag confidence={s.confidence} />
        </div>
      </div>

      {done ? (
        <div className="mx-5 mt-5 border border-accent-dim bg-surface px-4 py-3 text-sm text-fg">
          {done === "reject"
            ? "Ditolak."
            : done === "later"
              ? "Disimpan buat nanti."
              : "Disetujui. Draft lagi digarap, nanti masuk grup Telegram + tab Skrip."}
        </div>
      ) : (
        <div className="px-5 pt-5">
          <div className="mb-3 flex items-center justify-between">
            <WebSearchToggle on={web} set={setWeb} />
            <span className="text-[11px] text-faint">info terbaru, agak lebih mahal</span>
          </div>
          <button
            onClick={() => decide("approve")}
            disabled={!!acting}
            className="tap mb-2 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-accent font-semibold text-accent-fg disabled:opacity-60"
          >
            <IconCheck size={18} /> {acting === "approve" ? "..." : "Approve & bikin draft"}
          </button>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => decide("reject")}
              disabled={!!acting}
              className="tap flex h-11 items-center justify-center gap-1.5 rounded-xl border border-line text-sm text-fg active:bg-surface"
            >
              <IconX size={16} /> Tolak
            </button>
            <button
              onClick={() => decide("later")}
              disabled={!!acting}
              className="tap flex h-11 items-center justify-center gap-1.5 rounded-xl border border-line text-sm text-fg active:bg-surface"
            >
              <IconClock size={16} /> Nanti
            </button>
            <button
              onClick={() => decide("deep")}
              disabled={!!acting}
              className="tap flex h-11 items-center justify-center gap-1.5 rounded-xl border border-line text-sm text-fg active:bg-surface"
            >
              <IconSearch size={16} /> Riset
            </button>
          </div>
        </div>
      )}

      <div className="mt-6 flex items-center gap-5 border-y border-line px-5 py-4">
        <div className="flex items-baseline gap-2">
          <Score value={s.score?.final_score ?? 0} big />
          <span className="text-xs text-faint">/100</span>
        </div>
        <PriorityTag priority={s.score?.priority ?? null} />
        <span className="ml-auto text-[11px] uppercase tracking-widest text-faint">Skor akhir</span>
      </div>

      {s.score && (
        <Section title="Breakdown skor">
          <ScoreBars score={s.score} />
        </Section>
      )}

      <Section title="Ringkasan">
        <p className="text-sm leading-relaxed text-fg">{s.summary || "-"}</p>
      </Section>

      {s.research_pack && (
        <>
          {s.research_pack.angle && (
            <Section title="Angle">
              <p className="text-sm leading-relaxed text-fg">{s.research_pack.angle}</p>
            </Section>
          )}
          <Section title="Terbukti">
            <Bullets items={s.research_pack.proven} />
          </Section>
          <Section title="Spekulatif">
            <Bullets items={s.research_pack.speculative} />
          </Section>
        </>
      )}

      {entities.length > 0 && (
        <Section title="Entitas">
          <div className="flex flex-wrap gap-1.5">
            {entities.flatMap(([, arr]) =>
              (arr as string[]).map((e, i) => (
                <span key={`${e}-${i}`} className="border border-line px-2 py-1 text-xs text-muted">
                  {e}
                </span>
              )),
            )}
          </div>
        </Section>
      )}

      {s.source_url && (
        <Section title="Sumber">
          <a
            href={s.source_url}
            target="_blank"
            rel="noreferrer"
            className="tap flex items-center gap-2 text-sm text-accent"
          >
            <IconExternal size={15} /> <span className="truncate">{s.source_url}</span>
          </a>
        </Section>
      )}

      {s.scripts.length > 0 && (
        <Section title="Skrip">
          <Link href="/scripts" className="tap flex items-center gap-2 text-sm text-fg">
            <IconChevron size={15} className="text-accent" /> {s.scripts.length} versi, buka tab Skrip
          </Link>
        </Section>
      )}
    </div>
  );
}
