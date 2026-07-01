"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "Watchlist", match: (p: string) => p === "/" },
  { href: "/ticker", label: "Tickers", match: (p: string) => p.startsWith("/ticker") },
  { href: "/correlations", label: "Correlations", match: (p: string) => p.startsWith("/correlations") },
  { href: "/primer", label: "Primer", match: (p: string) => p.startsWith("/primer") },
  { href: "/methodology", label: "Methodology", match: (p: string) => p.startsWith("/methodology") },
];

export default function TabBar() {
  const path = usePathname() || "/";
  if (path.startsWith("/login")) return null;
  return (
    <nav className="sticky top-0 z-30 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-2xl gap-1 px-4">
        {tabs.map((t) => {
          const active = t.match(path);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`relative px-3 py-3 text-sm font-medium transition ${
                active ? "text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {t.label}
              {active && <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-sky-400" />}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
