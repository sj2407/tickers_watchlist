import Link from "next/link";
import { getLatestSnapshot, getLivePositions } from "@/lib/data";
import { getLiveQuotes } from "@/lib/quotes";
import { usd, pct, signClass } from "@/lib/format";
import { BadgeRow, LeanPill, SentimentChip, Metric } from "@/components/ui";
import RichText from "@/components/RichText";
import MoversChart, { type Mover } from "@/components/MoversChart";
import EarningsCalendar, { type EarningsEvent } from "@/components/EarningsCalendar";
import type { Lean } from "@/lib/types";

export const dynamic = "force-dynamic";

// Sort: things needing attention first (exit, trim, pile_on), then hold, then watch.
const leanRank: Record<string, number> = { exit: -1, trim: 0, pile_on: 1, hold: 2, watch: 3 };

export default async function Home() {
  const snap = await getLatestSnapshot();
  if (!snap) {
    return (
      <main className="min-h-dvh bg-zinc-950 p-6 text-zinc-300">
        <p>No snapshot yet. Run <code className="text-sky-400">python -m tracker.run --mode postclose</code>.</p>
      </main>
    );
  }

  const pf = snap.portfolio;
  const symbols = snap.tickers.map((t) => t.ticker);
  // Live quotes price the MONEY (book value + P&L + position values) to the current
  // market; the per-ticker quote and all commentary stay at the snapshot timestamp,
  // so the words never contradict the price. Falls back to snapshot prices with no key.
  const { quotes, asOf: liveAsOf } = await getLiveQuotes(symbols);
  const livePrices = Object.fromEntries(Object.entries(quotes).map(([s, q]) => [s, q.price]));
  const { book, byTicker, livePriced } = await getLivePositions(snap, livePrices);
  const liveTime = livePriced && liveAsOf
    ? new Date(liveAsOf * 1000).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }) + " ET"
    : null;
  const liveOn = Object.keys(byTicker).length > 0;
  const liveInvested = Object.values(byTicker).reduce((s, p) => s + (p.invested ?? 0), 0);
  const liveUnrealized = Object.values(byTicker).reduce((s, p) => s + (p.unrealized_pl ?? 0), 0);
  const bookValue = liveOn ? book : pf.book_value;
  const unrealized = liveOn ? liveUnrealized : pf.unrealized_pl;
  const returnPct = liveOn ? (liveInvested ? (liveUnrealized / liveInvested) * 100 : null) : pf.unrealized_pl_pct;
  const positionsCount = liveOn ? Object.values(byTicker).filter((p) => p.held).length : pf.positions_count;
  // Movers chart derives straight from day_change_pct (display), decoupled from the
  // big_move ALERT (which is mode-gated — suppressed at preopen where the change is
  // yesterday's move). The chart still shows on a preopen board; the alert doesn't.
  const bigMovePct = snap.thresholds?.big_move_pct ?? 7;
  const movers: Mover[] = snap.tickers
    .map((t) => ({ ticker: t.ticker, chg: t.price.day_change_pct ?? NaN }))
    .filter((m) => Number.isFinite(m.chg) && Math.abs(m.chg) >= bigMovePct);
  const otherAlerts = snap.alerts.filter((a) => a.type !== "big_move");
  const earningsEvents: EarningsEvent[] = snap.tickers
    .filter((t) => t.earnings?.next_date)
    .map((t) => ({
      ticker: t.ticker,
      date: t.earnings.next_date!,
      hour: t.earnings.next_hour ?? null,
      days: t.earnings.days_until_next ?? 999,
      held: t.position.held,
      est: t.earnings.next_date_estimated ?? false,
    }));
  const tickers = [...snap.tickers].sort((a, b) => {
    const la = (a.final_lean ?? a.signals.provisional_lean) as Lean;
    const lb = (b.final_lean ?? b.signals.provisional_lean) as Lean;
    if (leanRank[la] !== leanRank[lb]) return leanRank[la] - leanRank[lb];
    return Math.abs(b.price.day_change_pct ?? 0) - Math.abs(a.price.day_change_pct ?? 0);
  });

  return (
    <main className="min-h-dvh bg-zinc-950 pb-16 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6">
        <p className="mb-4 text-xs text-zinc-400">
          {snap.mode === "preopen" ? "Pre-open brief" : snap.mode === "intraday" ? "Intraday update" : "Post-close recap"}{" · as of "}
          {new Date(snap.generated_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York", timeZoneName: "short" })}
        </p>

        {/* Data-health banner (P8): degraded fetches must never look like quiet news */}
        {(snap.data_health?.finnhub_failures ?? 0) > 0 && (
          <p className="mb-4 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-200 ring-1 ring-amber-500/20">
            ⚠ {snap.data_health!.finnhub_failures} data {snap.data_health!.finnhub_failures === 1 ? "fetch" : "fetches"} failed
            on this run — some news, earnings or analyst data may be missing rather than quiet.
          </p>
        )}

        {/* Market recap — words first */}
        {(snap.market_recap || snap.macro_context) && (
          <section className="mb-5 rounded-2xl bg-gradient-to-b from-sky-950/40 to-zinc-900/60 p-5 ring-1 ring-zinc-800">
            <h2 className="mb-2 text-sm font-medium text-sky-300">Today&apos;s market</h2>
            {snap.market_recap && <p className="text-sm leading-relaxed text-zinc-200"><RichText text={snap.market_recap} symbols={symbols} /></p>}
            {snap.macro_context && (
              <p className="mt-2 border-t border-zinc-800 pt-2 text-xs leading-relaxed text-zinc-400">
                <span className="font-medium text-zinc-300">Macro: </span><RichText text={snap.macro_context} symbols={symbols} />
              </p>
            )}
          </section>
        )}

        {/* Portfolio snapshot */}
        <section className="mb-5 rounded-2xl bg-zinc-900/70 p-5 ring-1 ring-zinc-800">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-zinc-100">Your book</h2>
            {liveTime ? (
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />live · {liveTime}
              </span>
            ) : (
              <span className="text-[10px] text-zinc-500">priced at last update</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label="Book value" value={usd(bookValue)} hint="total market value" />
            <Metric label="Unrealized P/L" value={usd(unrealized)} className={signClass(unrealized)} hint="vs what you paid" />
            <Metric label="Return" value={pct(returnPct)} className={signClass(returnPct)} hint="since entry" />
            <Metric label="Positions" value={positionsCount} hint="names held" />
          </div>
          {pf.top_gainer && pf.top_loser && (
            <div className="mt-3 flex gap-4 border-t border-zinc-800 pt-3 text-xs text-zinc-400">
              <span>Best today: {pf.top_gainer[0]} <span className={signClass(pf.top_gainer[1])}>{pct(pf.top_gainer[1])}</span></span>
              <span>Worst: {pf.top_loser[0]} <span className={signClass(pf.top_loser[1])}>{pct(pf.top_loser[1])}</span></span>
            </div>
          )}
          {/* Sleeve scoreboard (P10): time-weighted, so trades/contributions are not "returns" */}
          {snap.performance && (
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-zinc-800 pt-3 text-xs text-zinc-400">
              <span>Sleeve since {new Date(snap.performance.since + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}:{" "}
                <span className={signClass(snap.performance.twr_pct)}>{pct(snap.performance.twr_pct)}</span>
              </span>
              {snap.performance.spy_pct != null && (
                <span>SPY <span className={signClass(snap.performance.spy_pct)}>{pct(snap.performance.spy_pct)}</span></span>
              )}
              {snap.performance.qqq_pct != null && (
                <span>QQQ <span className={signClass(snap.performance.qqq_pct)}>{pct(snap.performance.qqq_pct)}</span></span>
              )}
              {snap.performance.excess_vs_spy_pp != null && (
                <span>vs SPY <span className={signClass(snap.performance.excess_vs_spy_pp)}>{pct(snap.performance.excess_vs_spy_pp)}</span></span>
              )}
              {snap.performance.max_drawdown_pct != null && (
                <span>max drawdown <span className="text-zinc-300">{pct(snap.performance.max_drawdown_pct)}</span></span>
              )}
            </div>
          )}
        </section>

        {/* Big movers — labeled bar chart */}
        <MoversChart movers={movers} />

        {/* Other alerts (earnings) stay as pills */}
        {otherAlerts.length > 0 && (
          <section className="mb-5 space-y-1.5">
            {otherAlerts.map((a, i) => (
              <div key={i} className="flex items-center gap-2 rounded-lg bg-amber-500/5 px-3 py-2 text-sm text-amber-200 ring-1 ring-amber-500/15">
                <span className="text-amber-400">●</span>{a.msg}
              </div>
            ))}
          </section>
        )}

        {/* Earnings calendar */}
        <EarningsCalendar events={earningsEvents} today={snap.as_of_date} />

        {/* Ticker cards — takeaway first */}
        <h2 className="mb-2 text-sm font-semibold text-zinc-100">Your names</h2>
        <section className="space-y-3">
          {tickers.map((t) => {
            const lean = (t.final_lean ?? t.signals.provisional_lean) as Lean;
            return (
              <Link key={t.ticker} href={`/ticker/${t.ticker}`}
                className="block rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800 transition hover:ring-zinc-700">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold">{t.ticker}</span>
                    <LeanPill lean={lean} provisional={!t.final_lean} />
                    <SentimentChip sentiment={t.sentiment} />
                  </div>
                  <div className="flex items-baseline gap-2 text-right">
                    <span className="text-sm tabular-nums text-zinc-200">{usd(t.price.last)}</span>
                    <span className={`text-sm tabular-nums ${signClass(t.price.day_change_pct)}`}>{pct(t.price.day_change_pct)}</span>
                  </div>
                </div>

                {/* the plain-English takeaway is the hero line */}
                {t.takeaway ? (
                  <p className="mt-2 text-sm leading-relaxed text-zinc-200">
                    <RichText text={t.takeaway} symbols={symbols} />
                    {t.narrative_freshness === "stale" && t.narrative_as_of && (
                      <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-300">
                        read from {new Date(t.narrative_as_of).toLocaleString("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" })}
                      </span>
                    )}
                  </p>
                ) : (
                  <p className="mt-2 text-sm italic text-zinc-500">Awaiting the routine&apos;s read…</p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400">
                  {(byTicker[t.ticker]?.held ?? t.position.held) ? (
                    <>
                      <span>Value <span className="text-zinc-300">{usd((byTicker[t.ticker] ?? t.position).market_value)}</span></span>
                      <span>Since entry <span className={signClass((byTicker[t.ticker] ?? t.position).since_entry_pct)}>{pct((byTicker[t.ticker] ?? t.position).since_entry_pct)}</span></span>
                      <span>{pct((byTicker[t.ticker] ?? t.position).weight_pct, 0)} of book</span>
                    </>
                  ) : (
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-400">watch-only</span>
                  )}
                </div>
                <div className="mt-2"><BadgeRow badges={t.signals.badges} /></div>
              </Link>
            );
          })}
        </section>
      </div>
    </main>
  );
}
