import type { TradeRow } from "@/lib/data";
import { usd, num } from "@/lib/format";
import { SectionHeader } from "@/components/ui";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "America/New_York",
  });
}

// A plain-language log of every add/trim you've made on this name, newest first, with a
// running share count — so "review my strategy later" has something to review. The raw
// rows come from the append-only ledger (nothing is ever overwritten).
export default function TradeHistory({ trades }: { trades: TradeRow[] }) {
  if (!trades.length) return null;

  // Running position is computed forward (oldest → newest), then shown newest-first.
  let run = 0;
  const rows = trades.map((t) => {
    run += t.side === "buy" ? t.shares : -t.shares;
    return { ...t, run };
  });
  rows.reverse();

  return (
    <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <SectionHeader title="Trade history" accent="emerald" />
      <div className="mt-1 divide-y divide-zinc-800/70 text-[12px]">
        {rows.map((t, i) => (
          <div key={i} className="flex items-center gap-2 py-1.5">
            <span className="w-28 flex-none text-zinc-500">{fmtDate(t.executed_at)}</span>
            <span className={`w-10 flex-none font-medium ${t.side === "buy" ? "text-emerald-300" : "text-amber-300"}`}>
              {t.side === "buy" ? "Add" : "Trim"}
            </span>
            <span className="flex-1 text-zinc-300">{num(t.shares, 2)} sh @ {usd(t.price)}</span>
            <span className={`w-16 flex-none text-right ${t.side === "buy" ? "text-emerald-300" : "text-amber-300"}`}>
              {t.side === "buy" ? "+" : "−"}{usd(t.amount, 0)}
            </span>
            <span className="w-20 flex-none text-right text-zinc-500" title="position after this trade">
              {num(t.run, 2)} sh
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
