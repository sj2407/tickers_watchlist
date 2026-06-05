"use client";
import { useRouter } from "next/navigation";
import { useRef } from "react";

// The Tickers-tab switcher: a dropdown (held names first), prev/next arrows, and
// left/right swipe to step through names in the same order — so you never scroll
// the board to change names. Wraps the page body to catch the swipe; the chart is
// marked data-noswipe so panning it doesn't change tickers.
export default function TickerNav({
  order,
  held,
  watch,
  current,
  right,
  children,
}: {
  order: string[];
  held: string[];
  watch: string[];
  current: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const idx = Math.max(0, order.indexOf(current));
  const prev = order[(idx - 1 + order.length) % order.length];
  const next = order[(idx + 1) % order.length];
  const go = (s: string) => {
    if (s && s !== current) router.push(`/ticker/${s}`);
  };
  const sx = useRef(0);
  const sy = useRef(0);

  return (
    <>
      <div className="flex items-center justify-between gap-3 pt-1 pb-3">
        <div className="flex items-center gap-1">
          <button
            aria-label="Previous ticker"
            onClick={() => go(prev)}
            className="rounded-md px-2 py-1 text-lg leading-none text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
          >
            ‹
          </button>
          <div className="relative">
            <select
              aria-label="Switch ticker"
              value={current}
              onChange={(e) => go(e.target.value)}
              className="cursor-pointer appearance-none rounded-md bg-transparent pr-6 text-xl font-semibold text-zinc-100 focus:outline-none"
            >
              {held.length > 0 && (
                <optgroup label="Held">
                  {held.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </optgroup>
              )}
              {watch.length > 0 && (
                <optgroup label="Watching">
                  {watch.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            <span className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 text-sm text-zinc-500">▾</span>
          </div>
          <button
            aria-label="Next ticker"
            onClick={() => go(next)}
            className="rounded-md px-2 py-1 text-lg leading-none text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
          >
            ›
          </button>
        </div>
        {right}
      </div>
      <div
        onTouchStart={(e) => {
          sx.current = e.touches[0].clientX;
          sy.current = e.touches[0].clientY;
        }}
        onTouchEnd={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest("[data-noswipe]")) return;
          const dx = e.changedTouches[0].clientX - sx.current;
          const dy = e.changedTouches[0].clientY - sy.current;
          if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? next : prev);
        }}
      >
        {children}
      </div>
    </>
  );
}
