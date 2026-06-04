"""Rule-based signal layer.

Produces compact at-a-glance *badges* and a *provisional* pile/trim/hold lean
from purely quantitative rules. This is deliberately mechanical and transparent —
the Claude routine reads these signals plus the news/earnings context and writes
the *final* lean and rationale. We never pretend the rules are advice.
"""
from __future__ import annotations

from typing import Any


def build_signals(t: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    s = cfg["signals"]
    tech = t.get("technicals", {})
    pos = t.get("position", {})
    earn = t.get("earnings", {})
    badges: list[dict[str, str]] = []
    trim_pts: list[str] = []
    pile_pts: list[str] = []

    # --- trend ---
    trend = tech.get("trend")
    if trend == "uptrend":
        badges.append({"label": "Trend ↑", "tone": "good"})
        pile_pts.append("uptrend (price > 50d > 200d)")
    elif trend == "downtrend":
        badges.append({"label": "Trend ↓", "tone": "bad"})
        trim_pts.append("downtrend (price < 50d < 200d)")

    # --- RSI ---
    rsi = tech.get("rsi14")
    if rsi is not None:
        if rsi >= s["rsi_overbought"]:
            badges.append({"label": f"RSI {rsi:.0f}", "tone": "warn"})
            trim_pts.append(f"overbought (RSI {rsi:.0f})")
        elif rsi <= s["rsi_oversold"]:
            badges.append({"label": f"RSI {rsi:.0f}", "tone": "warn"})
            pile_pts.append(f"oversold (RSI {rsi:.0f})")

    # --- extended above 20d MA → trim watch ---
    d20 = tech.get("dist_sma20_pct")
    if d20 is not None and d20 >= s["extended_above_sma20_pct"]:
        badges.append({"label": f"+{d20:.0f}% vs 20d", "tone": "warn"})
        trim_pts.append(f"extended {d20:.0f}% above 20d MA")

    # --- volume conviction ---
    rv = tech.get("rel_volume")
    if rv is not None and rv >= s["rel_vol_spike"]:
        badges.append({"label": f"Vol {rv:.1f}x", "tone": "info"})

    # --- earnings proximity ---
    days = earn.get("days_until_next")
    if days is not None and 0 <= days <= s["earnings_soon_days"]:
        tone = "warn" if days <= 1 else "info"
        badges.append({"label": f"Earnings {days}d", "tone": tone})

    # NOTE: position weight is intentionally NOT a trim driver. This watchlist is a
    # small thematic satellite sleeve (>90% of the user's money is in diversified ETFs),
    # so concentration *within this sleeve* is not a risk. Trim only on thesis break.

    # --- analyst tilt ---
    rec = t.get("analyst")
    if rec:
        bulls = (rec.get("strongBuy") or 0) + (rec.get("buy") or 0)
        bears = (rec.get("sell") or 0) + (rec.get("strongSell") or 0)
        if bulls and bulls >= 3 * max(bears, 1):
            badges.append({"label": "Analysts bullish", "tone": "good"})
            pile_pts.append("analyst consensus tilts bullish")
        elif bears and bears >= bulls:
            badges.append({"label": "Analysts cautious", "tone": "bad"})
            trim_pts.append("analyst consensus tilts bearish")

    lean = _provisional_lean(pile_pts, trim_pts, days)
    return {
        "badges": badges,
        "provisional_lean": lean,
        "pile_points": pile_pts,
        "trim_points": trim_pts,
    }


def _provisional_lean(pile: list[str], trim: list[str], earnings_days: int | None) -> str:
    # Don't suggest sizing changes right before a print — event risk dominates.
    if earnings_days is not None and 0 <= earnings_days <= 1:
        return "hold"
    if len(trim) >= 2 and len(trim) > len(pile):
        return "trim"
    if len(pile) >= 2 and len(pile) > len(trim):
        return "pile_on"
    return "hold"
