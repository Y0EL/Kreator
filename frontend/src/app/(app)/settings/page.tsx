"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, clearToken } from "@/lib/api";
import { compact, useApi } from "@/lib/use-api";
import { fuzzy } from "@/lib/fuzzy";
import type { SourceItem } from "@/lib/types";
import {
  IconChevron,
  IconLogout,
  IconPlus,
  IconPower,
  IconSearch,
  IconTrash,
  IconX,
} from "@/components/icons";
import { PlatformIcon } from "@/components/brand-icon";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { ThemeToggle } from "@/components/theme-toggle";
import { PageHeader, Skeleton } from "@/components/ui";

const GROUPS: { key: string; label: string }[] = [
  { key: "wikipedia", label: "Wikipedia & Wiki" },
  { key: "rss", label: "RSS" },
  { key: "manual", label: "Manual & lainnya" },
];

function platformOf(s: SourceItem): string {
  if (s.type === "youtube" || (s.base_url || "").includes("youtube")) return "youtube";
  if (s.type === "mediawiki") return "wikipedia";
  if (s.type === "rss") return "rss";
  return "manual";
}

export default function SettingsPage() {
  const router = useRouter();
  const sources = useApi(() => api.sources(), []);
  const channels = useApi(() => api.youtubeChannels(), []);
  const me = useApi(() => api.youtubeMe(), []);

  const [q, setQ] = useState("");
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [confirm, setConfirm] = useState<{ title: string; body?: string; run: () => void } | null>(null);
  const [ytOpen, setYtOpen] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [addType, setAddType] = useState("youtube");
  const [addName, setAddName] = useState("");
  const [addVal, setAddVal] = useState("");
  const [busy, setBusy] = useState(false);

  const otherGroups = useMemo(() => {
    const rows = (sources.data || []).filter(
      (s) => platformOf(s) !== "youtube" && fuzzy(q, `${s.name} ${s.type}`),
    );
    return GROUPS.map((g) => ({
      ...g,
      items: rows.filter((s) => platformOf(s) === g.key),
    })).filter((g) => g.items.length > 0);
  }, [sources.data, q]);

  const ytChannels = useMemo(
    () => (channels.data || []).filter((c) => fuzzy(q, c.title || c.channel)),
    [channels.data, q],
  );

  function toggleSel(id: number) {
    setSel((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function addSource() {
    if (busy) return;
    setBusy(true);
    try {
      if (addType === "youtube") {
        if (!addVal.trim()) return;
        await api.addChannel(addVal.trim());
        channels.refetch();
      } else {
        if (!addName.trim() || !addVal.trim()) return;
        await api.addSource({ name: addName, type: "rss", feed_url: addVal.trim() });
        sources.refetch();
      }
      setAddName("");
      setAddVal("");
      setAddOpen(false);
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  async function toggle(s: SourceItem) {
    await api.patchSource(s.id, { status: s.status === "active" ? "paused" : "active" });
    sources.refetch();
  }

  function askDeleteSource(s: SourceItem) {
    setConfirm({
      title: `Hapus "${s.name}"?`,
      body: "Sumber ini beserta semua history-nya (item, story, skrip) dihapus permanen.",
      run: async () => {
        await api.deleteSource(s.id);
        setConfirm(null);
        sources.refetch();
      },
    });
  }

  function askBulkDelete() {
    const ids = [...sel];
    setConfirm({
      title: `Hapus ${ids.length} sumber?`,
      body: "Semua yang dipilih beserta history-nya dihapus permanen.",
      run: async () => {
        await api.bulkDeleteSources(ids);
        setConfirm(null);
        setSel(new Set());
        sources.refetch();
      },
    });
  }

  function askRemoveChannel(ref: string, title: string) {
    setConfirm({
      title: `Berhenti pantau "${title}"?`,
      body: "Channel ini ga dipantau lagi. Bahan yang udah ke-crawl tetap ada.",
      run: async () => {
        await api.removeChannel(ref);
        setConfirm(null);
        channels.refetch();
      },
    });
  }

  function logout() {
    clearToken();
    router.replace("/login");
  }

  const ch = me.data?.channel;

  return (
    <div className="pb-4">
      <PageHeader
        title="Atur"
        sub="Sumber & akun"
        right={
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={logout}
              aria-label="Keluar"
              className="tap flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-muted active:bg-accent-soft active:text-accent"
            >
              <IconLogout size={17} />
            </button>
            <button
              onClick={() => setAddOpen((o) => !o)}
              aria-label="Tambah sumber"
              className="tap flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-fg active:bg-surface-2"
            >
              <IconPlus size={18} className={addOpen ? "rotate-45 text-accent" : "text-muted"} />
            </button>
          </div>
        }
      />

      {/* Owner channel */}
      <Link
        href="/settings/me"
        className="tap card rise mx-5 mb-4 flex items-center gap-3 rounded-2xl p-4"
      >
        {ch?.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={ch.thumbnail} alt="" className="h-12 w-12 rounded-full" />
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-sm font-bold text-accent">
            YL
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-fg">
            {ch?.title || "@yoelmanoppo"}
          </div>
          <div className="tnum text-xs text-faint">
            {ch ? `${compact(ch.subscribers)} subs · ${compact(ch.views)} views` : "Lihat statistik channel"}
          </div>
        </div>
        <IconChevron size={18} className="text-faint" />
      </Link>

      {/* Search */}
      <div className="mx-5 mb-4 flex items-center gap-2 rounded-xl border border-line bg-surface px-3">
        <IconSearch size={16} className="text-faint" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Cari sumber atau channel"
          className="h-10 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-faint"
        />
        {q && (
          <button onClick={() => setQ("")} className="tap text-faint" aria-label="Bersihkan">
            <IconX size={15} />
          </button>
        )}
      </div>

      {addOpen && (
        <div className="card mx-5 mb-5 flex flex-col gap-2.5 rounded-2xl p-4">
          <div className="flex gap-2">
            {["youtube", "rss"].map((t) => (
              <button
                key={t}
                onClick={() => setAddType(t)}
                className={`tap flex-1 rounded-xl border py-2 text-xs font-medium uppercase tracking-wide ${
                  addType === t ? "border-accent bg-accent-soft text-accent" : "border-line text-faint"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          {addType === "rss" && (
            <input
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              placeholder="Nama sumber"
              className="h-11 rounded-xl bg-surface-2 px-3.5 text-sm text-fg outline-none placeholder:text-faint"
            />
          )}
          <input
            value={addVal}
            onChange={(e) => setAddVal(e.target.value)}
            placeholder={addType === "youtube" ? "channel (@handle / nama / channelId)" : "URL feed RSS"}
            className="h-11 rounded-xl bg-surface-2 px-3.5 text-sm text-fg outline-none placeholder:text-faint"
          />
          <button
            onClick={addSource}
            disabled={busy}
            className="tap h-11 rounded-xl bg-accent text-sm font-semibold text-accent-fg disabled:opacity-60"
          >
            {busy ? "..." : addType === "youtube" ? "Pantau channel" : "Tambah sumber"}
          </button>
        </div>
      )}

      {/* YouTube card */}
      <section className="mx-5 mb-4">
        <button
          onClick={() => setYtOpen((o) => !o)}
          className="tap card flex w-full items-center gap-3 rounded-2xl p-4"
        >
          <PlatformIcon platform="youtube" size={26} />
          <div className="min-w-0 flex-1 text-left">
            <div className="text-sm font-semibold text-fg">YouTube</div>
            <div className="text-xs text-faint">{(channels.data || []).length} channel dipantau</div>
          </div>
          <IconChevron size={18} className={`text-faint transition-transform ${ytOpen ? "rotate-90" : ""}`} />
        </button>
        {ytOpen && (
          <div className="mt-2 flex flex-col gap-2">
            {channels.loading ? (
              <Skeleton className="h-14" />
            ) : ytChannels.length > 0 ? (
              ytChannels.map((c) => (
                <div key={c.channel} className="card flex items-center gap-3 rounded-xl px-4 py-2.5">
                  {c.thumbnail ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.thumbnail} alt="" className="h-9 w-9 rounded-full" />
                  ) : (
                    <div className="h-9 w-9 rounded-full bg-surface-2" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-fg">{c.title || c.channel}</div>
                    <div className="tnum text-xs text-faint">{compact(c.subscribers)} subs</div>
                  </div>
                  <button
                    onClick={() => askRemoveChannel(c.channel, c.title || c.channel)}
                    className="tap rounded-lg p-2 text-muted active:text-accent"
                    aria-label="Berhenti pantau"
                  >
                    <IconX size={16} />
                  </button>
                </div>
              ))
            ) : (
              <p className="px-1 py-2 text-xs text-faint">
                Belum ada channel. Tambah lewat tombol + atau bilang ke bot Telegram.
              </p>
            )}
          </div>
        )}
      </section>

      {/* Other platform groups */}
      {sources.loading ? (
        <div className="flex flex-col gap-3 px-5">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : (
        otherGroups.map((g) => (
          <section key={g.key} className="mb-2">
            <div className="flex items-center gap-2 px-5 pb-2 pt-1">
              <PlatformIcon platform={g.key} size={18} />
              <h2 className="text-[11px] font-semibold uppercase tracking-widest text-faint">{g.label}</h2>
              <span className="tnum rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted">
                {g.items.length}
              </span>
            </div>
            {g.items.map((s) => (
              <div key={s.id} className="card mx-5 mb-3 flex items-center gap-3 rounded-2xl px-4 py-3">
                <button
                  onClick={() => toggleSel(s.id)}
                  aria-label="Pilih"
                  className={`tap flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${
                    sel.has(s.id) ? "border-accent bg-accent text-accent-fg" : "border-line text-transparent"
                  }`}
                >
                  <IconCheckTiny />
                </button>
                <span className={`h-2 w-2 shrink-0 rounded-full ${s.status === "active" ? "bg-accent" : "bg-faint"}`} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-fg">{s.name}</div>
                  <div className="text-xs text-faint">
                    <span className="uppercase tracking-wide">{s.type}</span> · {s.status}
                  </div>
                </div>
                <button onClick={() => toggle(s)} className="tap rounded-lg p-2 text-muted active:bg-surface-2">
                  <IconPower size={17} />
                </button>
                <button onClick={() => askDeleteSource(s)} className="tap rounded-lg p-2 text-muted active:text-accent">
                  <IconTrash size={17} />
                </button>
              </div>
            ))}
          </section>
        ))
      )}

      <p className="px-5 pt-6 text-center text-[11px] text-faint">Yoel - mesin editorial konten</p>

      {/* Bulk action bar */}
      {sel.size > 0 && (
        <div className="fixed inset-x-0 bottom-[calc(5.25rem+env(safe-area-inset-bottom))] z-30 px-4">
          <div className="mx-auto flex max-w-md items-center gap-3 rounded-2xl bg-fg px-4 py-3 text-bg shadow-lg">
            <span className="text-sm font-semibold">{sel.size} dipilih</span>
            <button onClick={() => setSel(new Set())} className="tap ml-auto text-xs opacity-80">
              Batal
            </button>
            <button
              onClick={askBulkDelete}
              className="tap flex items-center gap-1.5 rounded-xl bg-accent px-3 py-1.5 text-xs font-semibold text-accent-fg"
            >
              <IconTrash size={14} /> Hapus
            </button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.title || ""}
        body={confirm?.body}
        onConfirm={() => confirm?.run()}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}

function IconCheckTiny() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m5 12 5 5L20 6" />
    </svg>
  );
}
