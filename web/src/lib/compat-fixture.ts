// P0 backward-compat gate (compile-time): a minimal PRE-v3 snapshot literal.
// Every field the v3 phases add (rs_trend, revenue_yoy_q, narrative_freshness,
// data_health, performance, ...) must stay OPTIONAL in types.ts — if a later
// change makes one required, this file stops compiling and `tsc --noEmit` fails.
import type { Snapshot } from "./types";

export const PRE_V3_SNAPSHOT: Snapshot = {
  generated_at: "2026-06-09T17:00:00-04:00",
  mode: "postclose",
  session_phase: "afterhours",
  as_of_date: "2026-06-09",
  benchmark: "SPY",
  min_position_usd: 200,
  portfolio: {
    book_value: 1000,
    invested: 900,
    unrealized_pl: 100,
    unrealized_pl_pct: 11.11,
    positions_count: 1,
    top_gainer: ["AAA", 2.0],
    top_loser: ["AAA", 2.0],
  },
  tickers: [
    {
      ticker: "AAA",
      price: { last: 100, prev_close: 98, open: 99, day_high: 101, day_low: 97, day_change_pct: 2.04 },
      returns: { r1d: 2.04, r5d: 3.1, r20d: 8.2 },
      relative_strength: { rs5d: 1.0, rs20d: 0.2 },
      technicals: { rsi14: 55, trend: "uptrend" },
      fundamentals: { revenue_yoy: 20, gross_margin: 50 },
      thesis_break: { any: false },
      series: [{ t: "2026-06-09", o: 99, h: 101, l: 97, c: 100, v: 1000 }],
      position: { held: true, shares: 10, cost_basis: 90 },
      earnings: { next_date: "2026-06-16", days_until_next: 7 },
      analyst: { strongBuy: 5, buy: 3, hold: 2, sell: 0, strongSell: 0 },
      news: [],
      signals: { badges: [], provisional_lean: "hold", pile_points: [], trim_points: [] },
      takeaway: "carried",
      sentiment: "neutral",
      catalyst_summary: null,
      earnings_recap: null,
      final_lean: "hold",
      rationale: null,
    },
  ],
  market_recap: "carried",
  macro_context: null,
  alerts: [{ ticker: "AAA", type: "earnings_t7", msg: "AAA reports in ~1 week" }],
};
