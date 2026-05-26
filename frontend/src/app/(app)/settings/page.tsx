"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, clearToken } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { SourceItem } from "@/lib/types";
import { IconLogout, IconPlus, IconPower, IconTrash } from "@/components/icons";
import { ThemeToggle } from "@/components/theme-toggle";
import { Empty, PageHeader, Skeleton } from "@/components/ui";

const TYPE_LABEL: Record<string, string> = {
  youtube: "YouTube",
  rss: "RSS",
  mediawiki: "Wikipedia & Wiki",
  search: "Pencarian web",
  reddit: "Reddit",
  forum: "Forum",
  submission: "Manual",
  media: "Media",
  blog_archive: "Arsip blog",
};

export default function SettingsPage() {
  const router = useRouter();
  const { data, loading, refetch } = useApi(() => api.sources(), []);
  const groups = useMemo(() => {
    const m = new Map<string, SourceItem[]>();
    for (const s of data || []) {
      const arr = m.get(s.type) || [];
      arr.push(s);
      m.set(s.type, arr);
    }
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [data]);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("rss");
  const [name, setName] = useState("");
  const [val, setVal] = useState("");
  const [saving, setSaving] = useState(false);

  async function add() {
    if (!name.trim() || !val.trim()) return;
    setSaving(true);
    try {
      const body =
        type === "rss"
          ? { name, type, feed_url: val.trim() }
          : { name, type, channels: val.split(",").map((s) => s.trim()).filter(Boolean) };
      await api.addSource(body);
      setName("");
      setVal("");
      setOpen(false);
      refetch();
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  }

  async function toggle(s: SourceItem) {
    await api.patchSource(s.id, { status: s.status === "active" ? "paused" : "active" });
    refetch();
  }
  async function del(s: SourceItem) {
    await api.deleteSource(s.id);
    refetch();
  }
  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div>
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
              onClick={() => setOpen((o) => !o)}
              aria-label="Tambah sumber"
              className="tap flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-fg active:bg-surface-2"
            >
              <IconPlus size={18} className={open ? "rotate-45 text-accent" : "text-muted"} />
            </button>
          </div>
        }
      />

      {open && (
        <div className="card mx-5 mb-5 flex flex-col gap-2.5 rounded-2xl p-4">
          <div className="flex gap-2">
            {["rss", "youtube"].map((t) => (
              <button
                key={t}
                onClick={() => setType(t)}
                className={`tap flex-1 rounded-xl border py-2 text-xs font-medium uppercase tracking-wide ${
                  type === t ? "border-accent bg-accent-soft text-accent" : "border-line text-faint"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nama sumber"
            className="h-11 rounded-xl bg-surface-2 px-3.5 text-sm text-fg outline-none placeholder:text-faint"
          />
          <input
            value={val}
            onChange={(e) => setVal(e.target.value)}
            placeholder={type === "rss" ? "URL feed RSS" : "channel (@handle, pisah koma)"}
            className="h-11 rounded-xl bg-surface-2 px-3.5 text-sm text-fg outline-none placeholder:text-faint"
          />
          <button
            onClick={add}
            disabled={saving}
            className="tap h-11 rounded-xl bg-accent text-sm font-semibold text-accent-fg disabled:opacity-60"
          >
            {saving ? "..." : "Tambah sumber"}
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-3 px-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : groups.length > 0 ? (
        <div>
          {groups.map(([type, items]) => (
            <section key={type} className="mb-2">
              <div className="flex items-center gap-2 px-5 pb-2 pt-3">
                <h2 className="text-[11px] font-semibold uppercase tracking-widest text-faint">
                  {TYPE_LABEL[type] || type}
                </h2>
                <span className="tnum rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted">
                  {items.length}
                </span>
                <span className="ml-auto text-[11px] text-faint">
                  {items.filter((s) => s.status === "active").length} aktif
                </span>
              </div>
              {items.map((s) => (
                <div
                  key={s.id}
                  className="card mx-5 mb-3 flex items-center gap-3 rounded-2xl px-4 py-3"
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${
                      s.status === "active" ? "bg-accent" : "bg-faint"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-fg">{s.name}</div>
                    <div className="text-xs text-faint">
                      <span className="uppercase tracking-wide">{s.type}</span> · {s.status}
                    </div>
                  </div>
                  <button
                    onClick={() => toggle(s)}
                    className="tap rounded-lg p-2 text-muted active:bg-surface-2"
                  >
                    <IconPower size={17} />
                  </button>
                  <button
                    onClick={() => del(s)}
                    className="tap rounded-lg p-2 text-muted active:text-accent"
                  >
                    <IconTrash size={17} />
                  </button>
                </div>
              ))}
            </section>
          ))}
        </div>
      ) : (
        <Empty>Belum ada sumber.</Empty>
      )}

      <p className="px-5 pt-8 text-center text-[11px] text-faint">
        Yoel - mesin editorial konten
      </p>
    </div>
  );
}
