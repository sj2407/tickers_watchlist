import Link from "next/link";
import { notFound } from "next/navigation";
import { getTicker, getLatestSnapshot, getLivePositions } from "@/lib/data";
import { usd, pct, num, signClass, rsiWord, trendWord, earningsWhen, leanLabel, leanTextClass } from "@/lib/format";
import { LeanPill, SentimentChip, Metric, SectionHeader } from "@/components/ui";
import PriceChart from "@/components/PriceChart";
import PositionPanel from "@/components/PositionPanel";
import TickerNav from "@/components/TickerNav";
import RichText from "@/components/RichText";
import DecisionMatrix from "@/components/DecisionMatrix";
import { tickerOrder } from "@/lib/order";
import type { Lean } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TickerPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params; // Next 16: params is async
  const t = await getTicker(symbol);
  if (!t) notFound();
  const snap = await getLatestSnapshot();
  const minPos = snap?.min_position_usd ?? 200;
  const bench = snap?.benchmark ?? "SPY";

  // Position reflects the ledger LIVE (your trades show instantly); falls back to the
  // snapshot's position in file mode. The analysis (lean/technicals) is as-of-last-run.
  const { byTicker } = await getLivePositions(snap);
  const pos = byTicker[t.ticker] ?? t.position;

  // Ordered names for the switcher / swipe (held first, then watch-only).
  const heldSet = new Set(
    (snap?.tickers ?? []).filter((x) => byTicker[x.ticker]?.held ?? x.position.held).map((x) => x.ticker),
  );
  const { order, held, watch } = snap
    ? tickerOrder(snap, heldSet)
    : { order: [t.ticker], held: [t.ticker], watch: [] as string[] };

  const lean = (t.final_lean ?? t.signals.provisional_lean) as Lean;
  const asOf = snap?.generated_at
    ? new Date(snap.generated_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    : null;
  const symbols = (snap?.tickers ?? []).map((x) => x.ticker);
  const tech = t.technicals;
  const e = t.earnings;
  const a = t.analyst;

  return (
    <main className="min-h-dvh bg-zinc-950 pb-20 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-4">
        <TickerNav
          order={order}
          held={held}
          watch={watch}
          current={t.ticker}
          right={
            <div className="flex flex-col items-end gap-1">
              <div className="flex items-baseline gap-2">
                <span className="text-lg tabular-nums">{usd(t.price.last)}</span>
                <span className={`text-sm tabular-nums ${signClass(t.price.day_change_pct)}`}>{pct(t.price.day_change_pct)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <LeanPill lean={lean} provisional={!t.final_lean} />
                <SentimentChip sentiment={t.sentiment} />
              </div>
              {asOf && <span className="text-[10px] text-zinc-500">as of {asOf}</span>}
            </div>
          }
        >
          {/* Position — first, because it's what you check and act on most */}
          <div data-noswipe>
            <PositionPanel ticker={t.ticker} pos={pos} lastPrice={t.price.last} minPos={minPos} />
          </div>

          {/* The call, in plain English */}
          <section className="mt-4 rounded-2xl bg-gradient-to-b from-zinc-900 to-zinc-900/50 p-4 ring-1 ring-zinc-800">
            {t.takeaway && <p className="text-sm leading-relaxed text-zinc-200"><RichText text={t.takeaway} symbols={symbols} /></p>}
            <div className="mt-3 rounded-xl bg-zinc-950/60 p-3">
              <p className="text-xs uppercase tracking-wide text-zinc-300">Suggested action</p>
              <p className="text-sm text-zinc-100">
                <span className={`font-semibold ${leanTextClass(lean)}`}>{leanLabel(lean)}</span>
                {t.rationale ? <>: <RichText text={t.rationale.replace(/^(Hold|Trim|Pile on)\s*[—-]\s*/i, "")} symbols={symbols} /></> : null}
              </p>
            </div>
            {t.entry_guidance && (
              <p className="mt-2 text-sm text-zinc-300"><span className="text-zinc-400">Entry: </span><RichText text={t.entry_guidance} symbols={symbols} /></p>
            )}
            {t.invalidation && (
              <p className="mt-1.5 text-sm text-zinc-300"><span className="text-zinc-400">What would change this: </span><RichText text={t.invalidation} symbols={symbols} /></p>
            )}
            <p className="mt-2 text-[11px] text-zinc-500">Decision-support, not advice. You place every order. ${minPos} floor on trims. <Link href="/methodology" className="text-sky-400">How this is decided →</Link></p>
          </section>

          {/* Why this call — every metric placed on the action axis */}
          <DecisionMatrix t={t} />

          {/* What's happening — news & sentiment narrative */}
          {t.catalyst_summary && (
            <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
              <SectionHeader title="What's happening" accent="violet" />
              <p className="text-sm leading-relaxed text-zinc-200"><RichText text={t.catalyst_summary} symbols={symbols} /></p>
            </section>
          )}

          {/* Chart */}
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-3 ring-1 ring-zinc-800" data-noswipe>
            <PriceChart series={t.series} support={t.technicals.support_price} resistance={t.technicals.resistance_price} />
            <p className="px-1 pt-1 text-[11px] text-zinc-400">Daily candles · blue line = 50-day average · pinch / scroll to zoom</p>
          </section>

          {/* Momentum */}
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="Momentum" accent="sky" />
            <div className="grid grid-cols-3 gap-3">
              <Metric label="1 day" value={pct(t.returns.r1d)} className={signClass(t.returns.r1d)} />
              <Metric label="1 week" value={pct(t.returns.r5d)} className={signClass(t.returns.r5d)} />
              <Metric label="1 month" value={pct(t.returns.r20d)} className={signClass(t.returns.r20d)} />
              <Metric label={`vs ${bench} (1wk)`} value={pct(t.relative_strength.rs5d)} className={signClass(t.relative_strength.rs5d)} />
              <Metric label={`vs ${bench} (1mo)`} value={pct(t.relative_strength.rs20d)} className={signClass(t.relative_strength.rs20d)} />
              <Metric label="RSI" value={num(tech.rsi14, 0)} hint={rsiWord(tech.rsi14)} />
            </div>
          </section>

          {/* Trend & levels */}
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="Trend & levels" accent="sky" />
            <div className="grid grid-cols-3 gap-3">
              <Metric label="Trend" value={trendWord(tech.trend)} hint={tech.trend === "uptrend" ? "above key avgs" : tech.trend === "downtrend" ? "below key avgs" : "no clear direction"} />
              <Metric label="vs 50-day" value={pct(tech.dist_sma50_pct)} className={signClass(tech.dist_sma50_pct)} />
              <Metric label="vs 200-day" value={pct(tech.dist_sma200_pct)} className={signClass(tech.dist_sma200_pct)} />
              <Metric label="50/200 cross" value={(tech.ma_cross ?? "—").replace("_", " ")} hint="golden = bullish" />
              <Metric label="MACD" value={tech.macd_state ? tech.macd_state.replace("_", " ") : "—"} />
              <Metric label="From 52w high" value={pct(tech.dist_52w_high_pct)} className={signClass(tech.dist_52w_high_pct)} />
              <Metric label="Support" value={tech.support_price != null ? `${usd(tech.support_price)}` : "—"} hint={tech.support_dist_pct != null ? `${tech.support_dist_pct.toFixed(0)}% below` : undefined} />
              <Metric label="Resistance" value={tech.resistance_price != null ? `${usd(tech.resistance_price)}` : "—"} hint={tech.resistance_dist_pct != null ? `${tech.resistance_dist_pct.toFixed(0)}% above` : undefined} />
              <Metric label="Daily swing" value={pct(tech.atr14_pct)} hint="typical move" />
            </div>
          </section>

          {/* Fundamentals */}
          {t.fundamentals && (t.fundamentals.revenue_yoy != null || t.fundamentals.pe != null || t.fundamentals.gross_margin != null) && (
            <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
              <SectionHeader title="Fundamentals" accent="emerald">
                {t.fundamentals.report_date && (
                  <span className="text-[10px] text-zinc-500">as of Q ending {new Date(t.fundamentals.report_date + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" })}</span>
                )}
              </SectionHeader>
              <div className="grid grid-cols-3 gap-3">
                {t.fundamentals.revenue_yoy != null && <Metric label="Revenue growth" value={pct(t.fundamentals.revenue_yoy)} className={signClass(t.fundamentals.revenue_yoy)} hint="YoY" />}
                {t.fundamentals.eps_yoy != null && <Metric label="EPS growth" value={pct(t.fundamentals.eps_yoy)} className={signClass(t.fundamentals.eps_yoy)} hint="YoY" />}
                {t.fundamentals.gross_margin != null && <Metric label="Gross margin" value={`${t.fundamentals.gross_margin.toFixed(0)}%`} />}
                {t.fundamentals.pe != null && <Metric label="P/E" value={t.fundamentals.pe.toFixed(1)} hint="vs own history" />}
                {t.fundamentals.revenue_qoq_pct != null && <Metric label="Rev QoQ" value={pct(t.fundamentals.revenue_qoq_pct)} className={signClass(t.fundamentals.revenue_qoq_pct)} />}
              </div>
              {t.thesis_break?.any && (
                <p className="mt-3 rounded-lg bg-rose-500/10 px-3 py-2 text-xs text-rose-200 ring-1 ring-rose-500/20">
                  ⚠ Thesis-break flag(s):{" "}
                  {[
                    t.thesis_break.revenue_qoq_drop ? "revenue rolling over" : null,
                    t.thesis_break.margin_compression ? "margin compression" : null,
                    t.thesis_break.repeated_eps_miss ? "repeated EPS misses" : null,
                  ].filter(Boolean).join(", ")}
                </p>
              )}
            </section>
          )}

          {/* Earnings */}
          {(e.next_date || e.last_date) && (
            <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
              <SectionHeader title="Earnings" accent="amber" />
              {e.next_date && (
                <p className="text-sm text-zinc-200">
                  <span className="font-medium">Next report:</span> {new Date(e.next_date + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                  {e.next_hour && <span className="text-zinc-400"> ({e.next_hour === "amc" ? "after close" : e.next_hour === "bmo" ? "before open" : e.next_hour})</span>}
                  {e.days_until_next != null && <span className="text-zinc-400">, {earningsWhen(e.days_until_next)}</span>}
                </p>
              )}
              {e.next_eps_estimate != null && (
                <p className="mt-1 text-xs text-zinc-400">Street expects EPS ~{num(e.next_eps_estimate)}.</p>
              )}
              {e.last_eps_actual != null && (
                <p className="mt-2 text-sm text-zinc-400">
                  Last quarter: EPS {num(e.last_eps_actual)} vs {num(e.last_eps_estimate)} expected
                  {e.last_eps_surprise_pct != null && (
                    <span className={signClass(e.last_eps_surprise_pct)}> ({pct(e.last_eps_surprise_pct)} {e.last_eps_surprise_pct >= 0 ? "beat" : "miss"})</span>
                  )}
                </p>
              )}
              {t.earnings_recap && <p className="mt-2 text-sm leading-relaxed text-zinc-200"><RichText text={t.earnings_recap} symbols={symbols} /></p>}
            </section>
          )}

          {/* Analyst */}
          {a && (
            <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
              <SectionHeader title="What analysts think" accent="amber" />
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded bg-emerald-500/15 px-2 py-1 text-emerald-300">Strong buy {a.strongBuy ?? 0}</span>
                <span className="rounded bg-emerald-500/10 px-2 py-1 text-emerald-200">Buy {a.buy ?? 0}</span>
                <span className="rounded bg-zinc-700/40 px-2 py-1 text-zinc-300">Hold {a.hold ?? 0}</span>
                <span className="rounded bg-rose-500/10 px-2 py-1 text-rose-200">Sell {a.sell ?? 0}</span>
                {(a.strongSell ?? 0) > 0 && <span className="rounded bg-rose-500/15 px-2 py-1 text-rose-300">Strong sell {a.strongSell}</span>}
              </div>
            </section>
          )}

          {/* Headlines */}
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="Recent headlines" accent="violet" />
            <ul className="space-y-2">
              {t.news.length === 0 && <li className="text-sm text-zinc-400">No recent headlines.</li>}
              {t.news.map((n, i) => (
                <li key={i} className="text-sm">
                  <a href={n.url ?? "#"} target="_blank" rel="noreferrer" className="text-zinc-300 hover:text-sky-400">
                    {n.headline}
                  </a>
                  <span className="ml-2 text-xs text-zinc-500">
                    {n.source}{n.datetime ? ` · ${new Date(n.datetime).toLocaleDateString("en-US", { month: "short", day: "numeric" })}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </TickerNav>
      </div>
    </main>
  );
}
