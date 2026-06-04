import Link from "next/link";
import { notFound } from "next/navigation";
import { getTicker, getLatestSnapshot } from "@/lib/data";
import { usd, pct, num, signClass, rsiWord, trendWord, relVolWord, earningsWhen, leanLabel } from "@/lib/format";
import { BadgeRow, LeanPill, SentimentChip, Metric, SectionHeader } from "@/components/ui";
import PriceChart from "@/components/PriceChart";
import PositionEditor from "@/components/PositionEditor";
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

  const lean = (t.final_lean ?? t.signals.provisional_lean) as Lean;
  const tech = t.technicals;
  const e = t.earnings;
  const a = t.analyst;

  return (
    <main className="min-h-dvh bg-zinc-950 pb-20 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6">
        <Link href="/" className="text-sm text-sky-400">← Watchlist</Link>

        {/* Header */}
        <div className="mt-3 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{t.ticker}</h1>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-lg tabular-nums">{usd(t.price.last)}</span>
              <span className={`tabular-nums ${signClass(t.price.day_change_pct)}`}>{pct(t.price.day_change_pct)} today</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <LeanPill lean={lean} provisional={!t.final_lean} />
            <SentimentChip sentiment={t.sentiment} />
          </div>
        </div>

        {/* The call, in plain English — the hero of the page */}
        <section className="mt-4 rounded-2xl bg-gradient-to-b from-zinc-900 to-zinc-900/50 p-4 ring-1 ring-zinc-800">
          {t.takeaway && <p className="text-sm leading-relaxed text-zinc-200">{t.takeaway}</p>}
          <div className="mt-3 rounded-xl bg-zinc-950/60 p-3">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Suggested action</p>
            <p className="text-sm text-zinc-100">
              <span className="font-semibold">{leanLabel(lean)}</span>
              {t.rationale ? ` — ${t.rationale.replace(/^(Hold|Trim|Pile on)\s*[—-]\s*/i, "")}` : ""}
            </p>
            {!t.final_lean && <p className="mt-1 text-[11px] text-zinc-500">Auto-generated from signals — the routine refines this.</p>}
          </div>
          {t.entry_guidance && (
            <p className="mt-2 text-sm text-zinc-300"><span className="text-zinc-500">Entry: </span>{t.entry_guidance}</p>
          )}
          {t.invalidation && (
            <p className="mt-1.5 text-sm text-zinc-300"><span className="text-zinc-500">What would change this: </span>{t.invalidation}</p>
          )}
          <p className="mt-2 text-[11px] text-zinc-500">Decision-support, not advice — you place every order. ${minPos} floor on trims. <Link href="/methodology" className="text-sky-400">How this is decided →</Link></p>
        </section>

        {/* What's happening — news & sentiment narrative */}
        {t.catalyst_summary && (
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="What's happening" hint="The news that matters, and which way it cuts." />
            <p className="text-sm leading-relaxed text-zinc-200">{t.catalyst_summary}</p>
          </section>
        )}

        {/* Chart */}
        <section className="mt-4 rounded-2xl bg-zinc-900/70 p-3 ring-1 ring-zinc-800">
          <PriceChart series={t.series} support={t.technicals.support_price} resistance={t.technicals.resistance_price} />
          <p className="px-1 pt-1 text-[11px] text-zinc-500">Daily candles · blue line = 50-day average · pinch / scroll to zoom</p>
        </section>

        {/* Momentum — labeled with plain reads */}
        <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
          <SectionHeader title="Momentum" hint="How it's moved and whether it's running hot or cold." />
          <div className="grid grid-cols-3 gap-3">
            <Metric label="1 day" value={pct(t.returns.r1d)} className={signClass(t.returns.r1d)} />
            <Metric label="1 week" value={pct(t.returns.r5d)} className={signClass(t.returns.r5d)} hint="5 trading days" />
            <Metric label="1 month" value={pct(t.returns.r20d)} className={signClass(t.returns.r20d)} hint="20 trading days" />
            <Metric label={`vs ${bench} (1wk)`} value={pct(t.relative_strength.rs5d)} className={signClass(t.relative_strength.rs5d)} hint="beating market?" />
            <Metric label={`vs ${bench} (1mo)`} value={pct(t.relative_strength.rs20d)} className={signClass(t.relative_strength.rs20d)} hint="beating market?" />
            <Metric label="RSI" value={num(tech.rsi14, 0)} hint={rsiWord(tech.rsi14)} />
          </div>
        </section>

        {/* Trend & price levels */}
        <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
          <SectionHeader title="Trend & levels" hint="Where price sits versus its moving averages and 52-week range." />
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Trend" value={trendWord(tech.trend)} hint={tech.trend === "uptrend" ? "above key avgs" : tech.trend === "downtrend" ? "below key avgs" : "no clear direction"} />
            <Metric label="vs 50-day" value={pct(tech.dist_sma50_pct)} className={signClass(tech.dist_sma50_pct)} hint="medium-term" />
            <Metric label="vs 200-day" value={pct(tech.dist_sma200_pct)} className={signClass(tech.dist_sma200_pct)} hint="long-term" />
            <Metric label="50/200 cross" value={(tech.ma_cross ?? "—").replace("_", " ")} hint="golden = bullish" />
            <Metric label="MACD" value={tech.macd_state ? tech.macd_state.replace("_", " ") : "—"} hint="momentum" />
            <Metric label="From 52w high" value={pct(tech.dist_52w_high_pct)} className={signClass(tech.dist_52w_high_pct)} />
            <Metric label="Support" value={tech.support_price != null ? `${usd(tech.support_price)}` : "—"} hint={tech.support_dist_pct != null ? `${tech.support_dist_pct.toFixed(0)}% below` : "nearest"} />
            <Metric label="Resistance" value={tech.resistance_price != null ? `${usd(tech.resistance_price)}` : "—"} hint={tech.resistance_dist_pct != null ? `${tech.resistance_dist_pct.toFixed(0)}% above` : "nearest"} />
            <Metric label="Daily swing" value={pct(tech.atr14_pct)} hint="typical move (ATR)" />
          </div>
        </section>

        {/* Fundamentals */}
        {t.fundamentals && (t.fundamentals.revenue_yoy != null || t.fundamentals.pe != null || t.fundamentals.gross_margin != null) && (
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="Fundamentals" hint="Is the business itself still working?" />
            <div className="grid grid-cols-3 gap-3">
              <Metric label="Revenue growth" value={pct(t.fundamentals.revenue_yoy)} className={signClass(t.fundamentals.revenue_yoy)} hint="YoY" />
              <Metric label="EPS growth" value={pct(t.fundamentals.eps_yoy)} className={signClass(t.fundamentals.eps_yoy)} hint="YoY" />
              <Metric label="Gross margin" value={t.fundamentals.gross_margin != null ? `${t.fundamentals.gross_margin.toFixed(0)}%` : "—"} />
              <Metric label="P/E" value={t.fundamentals.pe != null ? t.fundamentals.pe.toFixed(1) : "—"} hint="vs own history" />
              <Metric label="Rev QoQ" value={pct(t.fundamentals.revenue_qoq_pct)} className={signClass(t.fundamentals.revenue_qoq_pct)} hint="sequential" />
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

        {/* Position + editor */}
        <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
          <h2 className="text-sm font-medium text-zinc-200">Your position</h2>
          <p className="mb-3 text-xs text-zinc-500">Records a trade — numbers refresh on the next run.</p>
          {t.position.held ? (
            <div className="grid grid-cols-3 gap-3">
              <Metric label="Shares" value={num(t.position.shares, 4)} />
              <Metric label="Avg cost" value={usd(t.position.cost_basis)} hint="what you paid" />
              <Metric label="Value" value={usd(t.position.market_value)} hint="worth now" />
              <Metric label="Invested" value={usd(t.position.invested)} />
              <Metric label="Gain/loss" value={usd(t.position.unrealized_pl)} className={signClass(t.position.unrealized_pl)} hint="unrealized" />
              <Metric label="Since entry" value={pct(t.position.since_entry_pct)} className={signClass(t.position.since_entry_pct)} />
              <Metric label="Weight" value={pct(t.position.weight_pct, 0)} hint="of total book" />
            </div>
          ) : (
            <p className="text-sm text-zinc-500">Watch-only — add shares to start tracking P/L.</p>
          )}
          {t.price.last != null && (
            <div className="mt-3">
              <PositionEditor ticker={t.ticker} position={t.position} lastPrice={t.price.last} minPositionUsd={minPos} />
            </div>
          )}
        </section>

        {/* Earnings */}
        {(e.next_date || e.last_date) && (
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="Earnings" hint="The biggest scheduled catalyst — watch the week and day before." />
            {e.next_date && (
              <p className="text-sm text-zinc-200">
                <span className="font-medium">Next report:</span> {new Date(e.next_date + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                {e.next_hour && <span className="text-zinc-500"> ({e.next_hour === "amc" ? "after close" : e.next_hour === "bmo" ? "before open" : e.next_hour})</span>}
                {e.days_until_next != null && <span className="text-zinc-400"> — {earningsWhen(e.days_until_next)}</span>}
              </p>
            )}
            {e.next_eps_estimate != null && (
              <p className="mt-1 text-xs text-zinc-500">Street expects EPS ~{num(e.next_eps_estimate)}.</p>
            )}
            {e.last_eps_actual != null && (
              <p className="mt-2 text-sm text-zinc-400">
                Last quarter: EPS {num(e.last_eps_actual)} vs {num(e.last_eps_estimate)} expected
                {e.last_eps_surprise_pct != null && (
                  <span className={signClass(e.last_eps_surprise_pct)}> ({pct(e.last_eps_surprise_pct)} {e.last_eps_surprise_pct >= 0 ? "beat" : "miss"})</span>
                )}
              </p>
            )}
            {t.earnings_recap && <p className="mt-2 text-sm leading-relaxed text-zinc-200">{t.earnings_recap}</p>}
          </section>
        )}

        {/* Analyst */}
        {a && (
          <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
            <SectionHeader title="What analysts think" hint={`Wall Street ratings (${a.period}).`} />
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
          <SectionHeader title="Recent headlines" hint="Raw feed — the summary above distills what actually matters." />
          <ul className="space-y-2">
            {t.news.length === 0 && <li className="text-sm text-zinc-500">No recent headlines.</li>}
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
      </div>
    </main>
  );
}
