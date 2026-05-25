"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconHome, IconPlay, IconScript, IconSliders, IconStack } from "./icons";

const tabs = [
  { href: "/", label: "Home", Icon: IconHome },
  { href: "/candidates", label: "Kandidat", Icon: IconStack },
  { href: "/scripts", label: "Skrip", Icon: IconScript },
  { href: "/youtube", label: "YouTube", Icon: IconPlay },
  { href: "/settings", label: "Atur", Icon: IconSliders },
];

export function TabBar() {
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 px-4 pt-2 pb-[max(0.7rem,env(safe-area-inset-bottom))]">
      <div className="card mx-auto flex max-w-md items-center justify-center gap-1.5 rounded-2xl p-2">
        {tabs.map(({ href, label, Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              aria-current={active ? "page" : undefined}
              className={`tap flex h-11 items-center justify-center rounded-xl transition-colors duration-300 ${
                active ? "bg-accent-soft px-3.5 text-accent" : "px-3 text-faint"
              }`}
            >
              <Icon size={20} className="shrink-0" />
              <span
                className={`overflow-hidden whitespace-nowrap text-sm font-semibold tracking-tight transition-all duration-300 ${
                  active ? "ml-2 max-w-[88px] opacity-100" : "ml-0 max-w-0 opacity-0"
                }`}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
