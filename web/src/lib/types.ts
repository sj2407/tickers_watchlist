// Shape of the snapshot produced by the Python pipeline (tracker/snapshot.py)
// and enriched by the Claude routine. Keep in sync with that module.

export type Lean = "pile_on" | "hold" | "trim" | "exit" | "watch";
export type Sentiment = "bullish" | "bearish" | "neutral" | "mixed";
export type BadgeTone = "good" | "bad" | "warn" | "info";

export interface Badge {
  label: string;
  tone: BadgeTone;
}

export interface PricePoint {
  t: string; // ISO date
  o: number;
  h: number;
  l: number;
  c: number;
  v: number | null;
}

export interface TickerPrice {
  last: number | null;
  prev_close: number | null;
  open: number | null;
  day_high: number | null;
  day_low: number | null;
  day_change_pct: number | null;
}

export interface Returns {
  r1d: number | null;
  r5d: number | null;
  r20d: number | null;
}

export interface Technicals {
  last_close?: number | null;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  dist_sma20_pct?: number | null;
  dist_sma50_pct?: number | null;
  dist_sma200_pct?: number | null;
  rsi14?: number | null;
  atr14?: number | null;
  atr14_pct?: number | null;
  high_52w?: number | null;
  low_52w?: number | null;
  dist_52w_high_pct?: number | null;
  dist_52w_low_pct?: number | null;
  avg_vol_20d?: number | null;
  rel_volume?: number | null;
  trend?: "uptrend" | "downtrend" | "mixed" | "n/a";
  macd_state?: "bullish_cross" | "bearish_cross" | "no_cross" | null;
  macd_hist?: number | null;
  ma_cross?: "golden_cross" | "death_cross" | "above" | "below" | "insufficient";
  support_dist_pct?: number | null;
  resistance_dist_pct?: number | null;
  support_price?: number | null;
  resistance_price?: number | null;
  breakout?: boolean;
  breakout_confirmed?: boolean;
}

export interface Fundamentals {
  source?: string | null;
  report_date?: string | null;
  fiscal_period?: string | null;
  revenue?: number | null;
  revenue_yoy?: number | null;
  revenue_qoq_pct?: number | null;
  eps?: number | null;
  eps_yoy?: number | null;
  eps_ttm?: number | null;
  gross_margin?: number | null;
  gross_margin_qoq_pp?: number | null;
  // P4: margin vs the same quarter last year (pp) — seasonality corroboration.
  gross_margin_yoy_pp?: number | null;
  // P7: single-quarter YoY from our own statements (the rules prefer these over
  // the cache's TTM growth, which revenue_yoy/eps_yoy hold for cache names).
  revenue_yoy_q?: number | null;
  eps_yoy_q?: number | null;
  // P7: cache TTM growth gated to null right after an earnings report.
  ttm_stale?: boolean;
  eps_miss_count_last3?: number | null;
  pe?: number | null;
  fundamentals_stale?: boolean;
}

export interface ThesisBreak {
  revenue_qoq_drop?: boolean | null;
  margin_compression?: boolean | null;
  repeated_eps_miss?: boolean | null;
  any?: boolean;
}

export interface Position {
  held: boolean;
  shares?: number;
  cost_basis?: number | null;
  market_value?: number;
  invested?: number;
  unrealized_pl?: number;
  since_entry_pct?: number | null;
  weight_pct?: number | null;
  notes?: string;
  target?: number | null;
  stop?: number | null;
}

export interface Earnings {
  next_date?: string;
  // P5: true when the date is a yfinance ESTIMATE (Finnhub didn't answer) —
  // treat as unconfirmed in any display.
  next_date_estimated?: boolean;
  days_until_next?: number | null;
  next_hour?: string | null;
  next_eps_estimate?: number | null;
  next_revenue_estimate?: number | null;
  last_date?: string;
  last_eps_estimate?: number | null;
  last_eps_actual?: number | null;
  last_revenue_estimate?: number | null;
  last_revenue_actual?: number | null;
  last_eps_surprise_pct?: number | null;
}

export interface Analyst {
  period?: string;
  strongBuy?: number;
  buy?: number;
  hold?: number;
  sell?: number;
  strongSell?: number;
}

export interface PriceTarget {
  low: number;
  median: number | null;
  mean: number | null;
  high: number;
  num_analysts: number | null;
  source?: string | null;
}

export interface NewsItem {
  datetime: string | null;
  headline: string | null;
  source: string | null;
  url: string | null;
  summary: string | null;
  category?: string | null;
}

export interface Signals {
  badges: Badge[];
  provisional_lean: Lean;
  pile_points: string[];
  trim_points: string[];
  drivers?: { pile: string[]; deterioration: string[]; blocks: string[]; review?: string | null };
}

export interface RelativeStrength {
  rs5d?: number | null;
  rs20d?: number | null;
  // P3: Mansfield/Weinstein regime — RS line (price ÷ SPY) vs its 50-session MA.
  rs_trend?: "outperforming" | "underperforming" | null;
  rs_line_ma50_dist_pct?: number | null;
}

export interface Ticker {
  ticker: string;
  price: TickerPrice;
  returns: Returns;
  relative_strength: RelativeStrength;
  technicals: Technicals;
  fundamentals?: Fundamentals | null;
  thesis_break?: ThesisBreak | null;
  series: PricePoint[];
  position: Position;
  earnings: Earnings;
  analyst: Analyst | null;
  price_target?: PriceTarget | null;
  news: NewsItem[];
  signals: Signals;
  // filled by the Claude routine (subscription):
  takeaway: string | null;
  sentiment: Sentiment | null;
  catalyst_summary: string | null;
  earnings_recap: string | null;
  final_lean: Lean | null;
  rationale: string | null;
  entry_guidance?: string | null;
  invalidation?: string | null;
  // validation provenance (P2): set when the pipeline coerced/rejected a
  // routine-written lean that broke the action vocabulary.
  lean_coerced_from?: string | null;
  lean_rejected?: string | null;
  // P8: when the routine last wrote this name's words + its age vs the numbers.
  narrative_as_of?: string | null;
  narrative_freshness?: "fresh" | "carried" | "stale" | null;
}

export interface Portfolio {
  book_value: number;
  invested: number;
  unrealized_pl: number;
  unrealized_pl_pct: number | null;
  positions_count: number;
  top_gainer: [string, number] | null;
  top_loser: [string, number] | null;
}

export interface Alert {
  ticker: string;
  type: string;
  msg: string;
}

export interface DataHealth {
  finnhub_calls?: number;
  finnhub_failures?: number;
  tickers_missing_news?: string[];
  tickers_missing_analyst?: string[];
  equity_cache_used?: boolean;
  equity_cache_age_hours?: number | null;
}

export interface Snapshot {
  generated_at: string;
  mode: "preopen" | "intraday" | "postclose";
  session_phase: string;
  as_of_date: string;
  benchmark: string;
  min_position_usd: number;
  portfolio: Portfolio;
  tickers: Ticker[];
  market_recap: string | null;
  macro_context: string | null;
  market_narrative_as_of?: string | null;
  alerts: Alert[];
  data_health?: DataHealth | null;
}

export interface PositionUpdate {
  ticker: string;
  shares: number;
  cost_basis: number | null;
  notes?: string;
  target?: number | null;
  stop?: number | null;
}
