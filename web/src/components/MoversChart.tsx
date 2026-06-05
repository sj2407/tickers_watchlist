import { pct } from "@/lib/format";

export interface Mover {
  ticker: string;
  chg: number; // day change %
}

// Labeled horizontal bar chart of today's big movers: bar length ∝ |move|, colored
// by direction, sorted biggest loser → biggest gainer. Replaces a flat list of
// "TICKER moved -X%" rows so magnitudes are comparable at a glance.
export default function MoversChart({ movers }: { movers: Mover[] }) {
  if (!movers.length) return null;
  const sorted = [...movers].sort((a, b) => a.chg - b.chg);
  const maxAbs = Math.max(...sorted.map((m) => Math.abs(m.chg)), 0.01);

  return (
    <section className="mb-5 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <h2 className="mb-3 text-sm font-semibold text-zinc-100">Big movers today</h2>
      <div className="space-y-1.5">
        {sorted.map((m) => {
          const up = m.chg >= 0;
          const w = Math.max(3, (Math.abs(m.chg) / maxAbs) * 100);
          return (
            <div key={m.ticker} className="flex items-center gap-2">
              <span className="w-11 shrink-0 text-xs font-semibold text-zinc-200">{m.ticker}</span>
              <div className="h-5 flex-1 rounded bg-zinc-800/40">
                <div
                  className={`h-full rounded ${up ? "bg-emerald-500/45" : "bg-rose-500/45"}`}
                  style={{ width: `${w}%` }}
                />
              </div>
              <span
                className={`w-14 shrink-0 text-right text-xs font-semibold tabular-nums ${up ? "text-emerald-300" : "text-rose-300"}`}
              >
                {pct(m.chg)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
