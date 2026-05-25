"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { IconSpinner } from "@/components/icons";

export default function LoginPage() {
  const router = useRouter();
  const [token, setTok] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim()) return;
    setLoading(true);
    setError(null);
    setToken(token.trim());
    try {
      await api.stats();
      router.replace("/");
    } catch {
      setError("Token salah atau server ga kebaca.");
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-7">
      <div className="mb-10">
        <div className="mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-accent">
          <span className="tnum text-2xl font-bold text-accent-fg">YL</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-fg">Yoel</h1>
        <p className="mt-1 text-sm text-muted">Mesin editorial konten. Masuk pakai token.</p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <input
          type="password"
          value={token}
          onChange={(e) => setTok(e.target.value)}
          placeholder="Dashboard token"
          autoFocus
          className="h-12 rounded-xl border border-line bg-surface px-4 text-fg outline-none ring-0 placeholder:text-faint focus:border-accent"
        />
        {error && <p className="text-sm text-accent">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="tap flex h-12 items-center justify-center gap-2 rounded-xl bg-accent font-semibold text-accent-fg disabled:opacity-60"
        >
          {loading ? <IconSpinner className="animate-spin" size={18} /> : "Masuk"}
        </button>
      </form>
    </main>
  );
}
