"use client";

import { useEffect, useState } from "react";
import { IconMoon, IconSun } from "./icons";

export function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    setLight(document.documentElement.classList.contains("light"));
  }, []);

  function toggle() {
    const el = document.documentElement;
    const next = !el.classList.contains("light");
    el.classList.toggle("light", next);
    try {
      localStorage.setItem("yoel_theme", next ? "light" : "dark");
    } catch {
      /* ignore */
    }
    setLight(next);
  }

  return (
    <button
      onClick={toggle}
      aria-label="Ganti tema"
      className="tap flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-muted active:bg-surface-2"
    >
      {light ? <IconMoon size={18} /> : <IconSun size={18} />}
    </button>
  );
}
