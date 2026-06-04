// Shape of the snapshot produced by the Python pipeline (tracker/snapshot.py)
// and enriched by the Claude routine. Keep in sync with that module.

export type Lean = "pile_on" | "trim" | "hold";
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
}

export interface Ticker {
  ticker: string;
  price: TickerPrice;
  returns: Returns;
  relative_strength: Record<string, number | null>;
  technicals: Technicals;
  series: PricePoint[];
  position: Position;
  earnings: Earnings;
  analyst: Analyst | null;
  news: NewsItem[];
  signals: Signals;
  // filled by the Claude routine (subscription):
  takeaway: string | null;
  sentiment: Sentiment | null;
  catalyst_summary: string | null;
  earnings_recap: string | null;
  final_lean: Lean | null;
  rationale: string | null;
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

export interface Snapshot {
  generated_at: string;
  mode: "preopen" | "postclose";
  session_phase: string;
  as_of_date: string;
  benchmark: string;
  min_position_usd: number;
  portfolio: Portfolio;
  tickers: Ticker[];
  market_recap: string | null;
  macro_context: string | null;
  alerts: Alert[];
}

export interface PositionUpdate {
  ticker: string;
  shares: number;
  cost_basis: number | null;
  notes?: string;
  target?: number | null;
  stop?: number | null;
}
