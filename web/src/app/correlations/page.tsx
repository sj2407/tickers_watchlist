import { getLatestSnapshot } from "@/lib/data";
import CorrelationMatrix from "@/components/CorrelationMatrix";

export const dynamic = "force-dynamic";
export const metadata = { title: "Correlations · Watchlist" };

export default async function CorrelationsPage() {
  const snap = await getLatestSnapshot();
  const rows = (snap?.tickers ?? []).filter((t) => t.series && t.series.length > 2);

  // Align every name onto the dates they ALL share, so correlations compare
  // like-for-like sessions (a newly-added name with less history won't misalign).
  const maps = rows.map((t) => new Map(t.series.map((p) => [p.t.slice(0, 10), p.c])));
  const common = rows.length
    ? [...maps[0].keys()].filter((d) => maps.every((m) => m.has(d))).sort()
    : [];
  const names = rows.map((t, i) => ({
    ticker: t.ticker,
    closes: common.map((d) => maps[i].get(d) as number),
  }));

  const enough = names.length >= 3 && common.length >= 30;

  return (
    <main className="min-h-dvh bg-zinc-950 pb-20 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6">
        <h1 className="text-xl font-semibold">How together does the book move — and crash?</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Rank co-movement and co-crash risk across your {names.length} watchlist names, from daily returns.
        </p>

        <div className="mt-5">
          {enough ? (
            <CorrelationMatrix names={names} asOf={snap?.as_of_date ?? "—"} />
          ) : (
            <div className="rounded-2xl bg-zinc-900/70 p-5 text-sm text-zinc-400 ring-1 ring-zinc-800">
              Not enough shared price history yet to compute correlations
              {names.length ? ` (${names.length} names, ${common.length} common days)` : ""}. Come back after a few more snapshots.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
