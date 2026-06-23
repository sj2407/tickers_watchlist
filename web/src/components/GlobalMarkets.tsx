import { pct, signClass } from "@/lib/format";
import type { GlobalMarkets as GlobalMarketsData } from "@/lib/types";

// Overnight / global markets that move the US open. Deterministic + refreshed every
// run (never carried), so the pre-open brief always shows live Asia/Europe/futures
// even when the LLM narrative didn't regenerate. Grouped by region in fetch order.
const REGION_ORDER = ["Asia", "Europe", "US futures"];

export default function GlobalMarkets({ data }: { data: GlobalMarketsData | null | undefined }) {
  if (!data || data.markets.length === 0) return null;

  const byRegion = new Map<string, typeof data.markets>();
  for (const m of data.markets) {
    const arr = byRegion.get(m.region) ?? [];
    arr.push(m);
    byRegion.set(m.region, arr);
  }
  const regions = [
    ...REGION_ORDER.filter((r) => byRegion.has(r)),
    ...[...byRegion.keys()].filter((r) => !REGION_ORDER.includes(r)),
  ];
  const asOf = new Date(data.as_of).toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit", timeZone: "America/New_York",
  });

  return (
    <section className="mb-5 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-zinc-200">Overnight &amp; global</h2>
        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-300">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />live · {asOf} ET
        </span>
      </div>
      <div className="space-y-2.5">
        {regions.map((region) => (
          <div key={region}>
            <p className="mb-1 text-[10px] uppercase tracking-wide text-zinc-500">{region}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {byRegion.get(region)!.map((m) => (
                <span key={m.symbol} className="text-sm tabular-nums text-zinc-300">
                  {m.label} <span className={signClass(m.change_pct)}>{pct(m.change_pct)}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
