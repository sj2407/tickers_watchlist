"use client";
import { useMemo, useState } from "react";
import Link from "next/link";

export interface EarningsEvent {
  ticker: string;
  date: string; // YYYY-MM-DD
  hour: string | null;
  days: number;
  held: boolean;
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function ymd(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function EarningsCalendar({ events, today }: { events: EarningsEvent[]; today: string }) {
  const byDay = useMemo(() => {
    const m: Record<string, EarningsEvent[]> = {};
    for (const e of events) (m[e.date] ??= []).push(e);
    return m;
  }, [events]);

  // start on the month of the soonest upcoming earnings (fallback: today's month)
  const firstDate = events.length ? events.map((e) => e.date).sort()[0] : today;
  const [cursor, setCursor] = useState(() => {
    const d = new Date(firstDate + "T00:00:00");
    return { y: d.getFullYear(), m: d.getMonth() };
  });
  const [selected, setSelected] = useState<string | null>(firstDate >= today ? firstDate : null);

  const monthStart = new Date(cursor.y, cursor.m, 1);
  const daysInMonth = new Date(cursor.y, cursor.m + 1, 0).getDate();
  const leadBlanks = monthStart.getDay();
  const cells: (number | null)[] = [
    ...Array(leadBlanks).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const shift = (delta: number) => {
    const m = cursor.m + delta;
    setCursor({ y: cursor.y + Math.floor(m / 12), m: ((m % 12) + 12) % 12 });
  };

  const selectedEvents = selected ? (byDay[selected] ?? []) : [];

  return (
    <section className="mb-5 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-100">📅 Earnings calendar</h2>
        <div className="flex items-center gap-1">
          <button onClick={() => shift(-1)} className="rounded-md px-2 py-1 text-zinc-400 hover:bg-zinc-800">‹</button>
          <span className="w-28 text-center text-sm text-zinc-300">{MONTHS[cursor.m]} {cursor.y}</span>
          <button onClick={() => shift(1)} className="rounded-md px-2 py-1 text-zinc-400 hover:bg-zinc-800">›</button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center">
        {WEEKDAYS.map((d, i) => (
          <div key={i} className="pb-1 text-[10px] font-medium uppercase text-zinc-400">{d}</div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={i} />;
          const date = ymd(new Date(cursor.y, cursor.m, day));
          const evs = byDay[date] ?? [];
          const isToday = date === today;
          const isSel = date === selected;
          const soon = evs.some((e) => e.days >= 0 && e.days <= 1);
          const week = evs.some((e) => e.days >= 0 && e.days <= 7);
          const has = evs.length > 0;
          return (
            <button
              key={i}
              onClick={() => has && setSelected(isSel ? null : date)}
              disabled={!has}
              className={[
                "relative aspect-square rounded-lg text-xs transition",
                isSel ? "ring-2 ring-sky-400" : "",
                isToday ? "bg-zinc-800 font-semibold text-zinc-100" : "text-zinc-400",
                has ? "cursor-pointer hover:bg-zinc-800" : "cursor-default",
              ].join(" ")}
            >
              <span className="absolute left-0 right-0 top-1">{day}</span>
              {has && (
                <span
                  className={[
                    "absolute bottom-1 left-1/2 -translate-x-1/2 rounded-full px-1.5 text-[9px] font-semibold leading-4",
                    soon ? "bg-rose-500/30 text-rose-200" : week ? "bg-amber-500/25 text-amber-200" : "bg-sky-500/25 text-sky-200",
                  ].join(" ")}
                >
                  {evs.length === 1 ? evs[0].ticker : `${evs.length}×`}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* detail for the selected day */}
      <div className="mt-3 border-t border-zinc-800 pt-3">
        {selected && selectedEvents.length > 0 ? (
          <>
            <p className="mb-2 text-xs text-zinc-500">
              {new Date(selected + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            </p>
            <div className="flex flex-wrap gap-2">
              {selectedEvents.map((e) => (
                <Link key={e.ticker} href={`/ticker/${e.ticker}`}
                  className="flex items-center gap-1.5 rounded-lg bg-zinc-800 px-2.5 py-1.5 text-sm text-zinc-100 ring-1 ring-zinc-700 hover:ring-sky-500">
                  <span className="font-medium">{e.ticker}</span>
                  {e.hour && <span className="text-[10px] text-zinc-500">{e.hour === "amc" ? "after close" : e.hour === "bmo" ? "before open" : e.hour}</span>}
                  {e.days >= 0 && e.days <= 1 && <span className="rounded bg-rose-500/20 px-1 text-[9px] text-rose-300">T‑1</span>}
                </Link>
              ))}
            </div>
          </>
        ) : (
          <p className="text-xs text-zinc-400">Tap a highlighted day to see which names report. Red = reports today/tomorrow.</p>
        )}
      </div>
    </section>
  );
}
