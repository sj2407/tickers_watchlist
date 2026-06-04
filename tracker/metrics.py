"""Metrics registry — the SINGLE SOURCE OF TRUTH for what every number means.

The pipeline tags each Signal with a `metric` key from here; the web glossary
(/methodology) is generated from this same registry (see tools/export_metrics.py),
so the explanation can never silently drift from the thing it explains.

Each entry: label, category, definition (plain English), how_computed, good_when,
source_type. `source_ref` is attached per-run on the Signal, not here.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = {
    "technical", "momentum", "fundamental", "risk", "thesis", "event", "analyst", "position",
}
SOURCE_TYPES = {
    "chart_data", "market_data", "valuation_data", "filing_data",
    "company_disclosure", "event_data", "user_defined",
}


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    category: str
    definition: str
    how_computed: str
    good_when: str
    source_type: str


def _m(*a) -> MetricDef:
    return MetricDef(*a)


# Ordered for nice glossary rendering.
REGISTRY: dict[str, MetricDef] = {m.key: m for m in [
    # ── technical ────────────────────────────────────────────────────
    _m("rsi14", "RSI (14)", "technical",
       "Momentum oscillator from 0–100; how hot or cold the recent move is.",
       "Wilder's RSI over the last 14 daily closes.",
       "30–70 is neutral; <30 oversold (possible add timing); >70 overbought (don't chase).",
       "chart_data"),
    _m("macd", "MACD", "technical",
       "Trend/momentum crossover signal.",
       "EMA(12) − EMA(26) vs its 9-day signal line; we read the latest crossover.",
       "A bullish cross is favorable; a bearish cross is caution.",
       "chart_data"),
    _m("ma_cross", "50/200-day cross", "technical",
       "Medium-term vs long-term trend relationship.",
       "State of SMA(50) vs SMA(200): golden/death cross, or above/below.",
       "Golden cross / 50 above 200 = uptrend; death cross / below = downtrend.",
       "chart_data"),
    _m("trend", "Trend", "technical",
       "Overall direction of the price.",
       "Price vs the 50-day, and the 50-day vs the 200-day.",
       "Uptrend (price > 50d > 200d) is favorable.",
       "chart_data"),
    _m("dist_sma20_pct", "vs 20-day avg", "technical",
       "How far price sits above/below its short-term average.",
       "(close / SMA20 − 1) × 100.",
       "Far above (≥~12%) = extended/overbought zone — wait for a pullback, don't chase.",
       "chart_data"),
    _m("dist_sma50_pct", "vs 50-day avg", "technical",
       "How far price sits above/below its medium-term average.",
       "(close / SMA50 − 1) × 100.",
       "Modestly above in an uptrend is healthy; far above = extended (don't chase).",
       "chart_data"),
    _m("dist_sma200_pct", "vs 200-day avg", "technical",
       "Price vs its long-term average.",
       "(close / SMA200 − 1) × 100.",
       "Above the 200-day is a long-term uptrend.",
       "chart_data"),
    _m("dist_52w_high_pct", "From 52-week high", "technical",
       "How far below the past year's high.",
       "(close / max(last 252 closes) − 1) × 100.",
       "Near 0% = relative strength.",
       "chart_data"),
    _m("support_dist_pct", "Distance to support", "technical",
       "How far above the nearest support level.",
       "% above the nearest swing-low pivot below price.",
       "Near support = tightly definable risk and a better add zone.",
       "chart_data"),
    _m("resistance_dist_pct", "Distance to resistance", "technical",
       "How far below the nearest resistance level.",
       "% below the nearest swing-high pivot above price.",
       "A confirmed break above resistance signals momentum.",
       "chart_data"),
    _m("rel_volume", "Relative volume", "technical",
       "Today's volume vs its recent average — conviction behind the move.",
       "latest volume / mean(prior 20 sessions).",
       "≥1.5× confirms a breakout/breakdown; light volume = less conviction.",
       "market_data"),
    _m("atr14_pct", "Daily swing (ATR%)", "technical",
       "How much the stock typically moves in a day.",
       "ATR(14) ÷ price × 100.",
       "Context: a 4% move is normal for a high-ATR name, alarming for a low one.",
       "chart_data"),
    _m("breakout", "Breakout", "technical",
       "Whether price just made a new short-term high.",
       "close > max(prior 20 closes); 'confirmed' adds ≥1.5× volume.",
       "A volume-confirmed breakout is a momentum signal.",
       "chart_data"),
    # ── momentum / relative strength ─────────────────────────────────
    _m("ret_1d", "1-day return", "momentum", "Price change today.", "(close/prev_close − 1) × 100.", "Context, not a signal alone.", "market_data"),
    _m("ret_5d", "1-week return", "momentum", "Move over 5 trading days.", "Trailing 5-session return.", "Sustained strength is favorable.", "market_data"),
    _m("ret_20d", "1-month return", "momentum", "Move over ~20 trading days.", "Trailing 20-session return.", "Sustained strength is favorable.", "market_data"),
    _m("rs_5d", "Rel. strength vs SPY (1wk)", "momentum",
       "Is it beating the market this week?",
       "Ticker 5-day return − SPY 5-day return.",
       "Positive = leading the market (idiosyncratic strength).", "market_data"),
    _m("rs_20d", "Rel. strength vs SPY (1mo)", "momentum",
       "Is it beating the market this month?",
       "Ticker 20-day return − SPY 20-day return.",
       "Positive = leading; sustained negative = a deterioration signal.", "market_data"),
    # ── fundamental ──────────────────────────────────────────────────
    _m("revenue_growth_yoy", "Revenue growth (YoY)", "fundamental",
       "Is the top line still growing?",
       "(latest-quarter revenue / same quarter a year ago − 1) × 100.",
       "Stable or accelerating; 15%+ for growth names. Deceleration is a warning.",
       "filing_data"),
    _m("eps_growth_yoy", "EPS growth (YoY)", "fundamental",
       "Is profit per share growing?",
       "(latest-quarter EPS / a year ago − 1) × 100.",
       "Stable/accelerating, roughly tracking revenue. Deterioration is a warning.",
       "filing_data"),
    _m("gross_margin", "Gross margin", "fundamental",
       "Profitability of each sale.",
       "Gross profit ÷ revenue, latest quarter.",
       "Stable or expanding. Falling margins can signal a broken thesis.",
       "filing_data"),
    _m("pe_vs_history", "P/E vs own history", "fundamental",
       "Is it expensive relative to its own past?",
       "Current P/E (price ÷ trailing-4Q EPS) vs its ~8-quarter range.",
       "At/below its own history is fine if growth is intact; stretched + slowing growth is caution.",
       "valuation_data"),
    # ── risk / trade-plan (informational; never auto-acts) ───────────
    _m("since_entry_pct", "Since entry", "position",
       "Your return since you bought it.",
       "(price / your average cost − 1) × 100.",
       "Informational — not a buy/sell trigger on its own.", "user_defined"),
    _m("weight_pct", "Weight of book", "position",
       "This position as a % of THIS watchlist sleeve.",
       "position market value ÷ total book value.",
       "INFORMATIONAL ONLY. Never a reason to trim — this is a small satellite sleeve.",
       "user_defined"),
    _m("dist_to_stop_pct", "Distance to stop", "risk",
       "How far price is above your stop level (if set).",
       "(price / stop − 1) × 100.",
       "A breached stop is a prompt to re-check the thesis — not an auto-cut.", "user_defined"),
    _m("dist_to_target_pct", "Distance to target", "risk",
       "How far below your price target (if set).",
       "(target / price − 1) × 100.",
       "Hitting a target is a prompt to reassess, not a forced sell.", "user_defined"),
    _m("reward_risk", "Reward : risk", "risk",
       "Upside to target vs downside to stop.",
       "(target − price) ÷ (price − stop).",
       "≥ 2:1 is a healthier setup. Informational.", "user_defined"),
    # ── thesis-break flags (can push toward trim/exit) ───────────────
    _m("tb_revenue_qoq_drop", "Revenue rolling over", "thesis",
       "Sequential revenue decline — a deterioration signal.",
       "Latest-quarter revenue falls vs the prior quarter by ≥ threshold.",
       "False is good. True contributes to a trim/exit case.", "filing_data"),
    _m("tb_margin_compression", "Margin compression", "thesis",
       "Gross margin falling quarter-over-quarter.",
       "Gross margin drops vs the prior quarter by ≥ threshold (pp).",
       "False is good. True contributes to a trim/exit case.", "filing_data"),
    _m("tb_repeated_eps_miss", "Repeated EPS misses", "thesis",
       "Consistently missing estimates — execution concern.",
       "≥2 of the last 3 quarters reported EPS below estimate.",
       "False is good. True is a strong deterioration signal.", "filing_data"),
    # ── event / analyst ──────────────────────────────────────────────
    _m("days_to_earnings", "Days to earnings", "event",
       "Time until the next report — the biggest scheduled catalyst.",
       "Calendar days to the next confirmed earnings date.",
       "≤7 = watch closely; ≤1 = don't size into the print.", "event_data"),
    _m("analyst_consensus", "Analyst consensus", "analyst",
       "Wall Street's buy/hold/sell tilt.",
       "Counts of strong-buy/buy/hold/sell/strong-sell.",
       "A strong buy tilt is supportive; a bearish tilt is caution.", "market_data"),
]}


def all_keys() -> set[str]:
    return set(REGISTRY.keys())


def get(key: str) -> MetricDef | None:
    return REGISTRY.get(key)


def as_glossary() -> list[dict]:
    """Serializable list for the web glossary (single source → no drift)."""
    return [
        {"key": m.key, "label": m.label, "category": m.category,
         "definition": m.definition, "how_computed": m.how_computed,
         "good_when": m.good_when, "source_type": m.source_type}
        for m in REGISTRY.values()
    ]
