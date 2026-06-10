"""Rule-based signal layer.

Produces compact at-a-glance *badges* and a *provisional* pile/trim/hold lean
from purely quantitative rules. This is deliberately mechanical and transparent —
the Claude routine reads these signals plus the news/earnings context and writes
the *final* lean and rationale. We never pretend the rules are advice.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from . import metrics


@dataclass
class Signal:
    """One evaluated metric. Every chip the UI shows comes from one of these;
    `metric` references a key in metrics.REGISTRY (provenance + glossary link)."""
    category: str
    metric: str                     # must be a metrics.REGISTRY key
    value_num: float | None = None
    value_text: str | None = None
    passed: bool | None = None      # None = insufficient data
    suggestion: str | None = None
    source_type: str | None = None
    source_ref: str | None = None
    insufficient_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def signal(metric_key: str, *, value_num=None, value_text=None, passed=None,
           suggestion=None, source_ref=None) -> Signal:
    """Build a Signal from a registry key, pulling category/source_type from the
    registry so they can't drift. Unknown key → ValueError (caught by tests)."""
    md = metrics.get(metric_key)
    if md is None:
        raise ValueError(f"unknown metric key {metric_key!r} (not in metrics.REGISTRY)")
    return Signal(
        category=md.category,
        metric=metric_key,
        value_num=value_num,
        value_text=value_text,
        passed=passed,
        suggestion=suggestion,
        source_type=md.source_type,
        source_ref=source_ref,
        insufficient_data=(value_num is None and value_text is None and passed is None),
    )


def build_signals(t: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    s = cfg["signals"]
    tech = t.get("technicals", {})
    pos = t.get("position", {})
    earn = t.get("earnings", {})
    badges: list[dict[str, str]] = []

    # Badges are display-only chips. The lean is computed solely in provisional_lean()
    # (below) — we deliberately do NOT accumulate trim/pile "points" here, so an
    # overbought or extended reading can NEVER leak into a trim (see plan C3).

    # --- trend ---
    trend = tech.get("trend")
    if trend == "uptrend":
        badges.append({"label": "Trend ↑", "tone": "good"})
    elif trend == "downtrend":
        badges.append({"label": "Trend ↓", "tone": "bad"})

    # --- RSI ---
    rsi = tech.get("rsi14")
    if rsi is not None and (rsi >= s["rsi_overbought"] or rsi <= s["rsi_oversold"]):
        badges.append({"label": f"RSI {rsi:.0f}", "tone": "warn"})

    # --- extended above 20d MA (don't-chase flag, not a trim) ---
    d20 = tech.get("dist_sma20_pct")
    if d20 is not None and d20 >= s["extended_above_sma20_pct"]:
        badges.append({"label": f"+{d20:.0f}% vs 20d", "tone": "warn"})

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
    # so concentration *within this sleeve* is not a risk.

    # --- analyst tilt (badge only) ---
    rec = t.get("analyst")
    if rec:
        bulls = (rec.get("strongBuy") or 0) + (rec.get("buy") or 0)
        bears = (rec.get("sell") or 0) + (rec.get("strongSell") or 0)
        if bulls and bulls >= 3 * max(bears, 1):
            badges.append({"label": "Analysts bullish", "tone": "good"})
        elif bears and bears >= bulls:
            badges.append({"label": "Analysts cautious", "tone": "bad"})

    # MACD + cross badges (from the ported technicals)
    if tech.get("macd_state") == "bullish_cross":
        badges.append({"label": "MACD ↑", "tone": "good"})
    elif tech.get("macd_state") == "bearish_cross":
        badges.append({"label": "MACD ↓", "tone": "bad"})
    if tech.get("ma_cross") == "golden_cross":
        badges.append({"label": "Golden cross", "tone": "good"})
    elif tech.get("ma_cross") == "death_cross":
        badges.append({"label": "Death cross", "tone": "bad"})

    # fundamentals + thesis-break badges
    fund = t.get("fundamentals", {}) or {}
    if fund.get("revenue_yoy") is not None:
        rg = fund["revenue_yoy"]
        badges.append({"label": f"Rev {rg:+.0f}% YoY", "tone": "good" if rg >= 15 else ("bad" if rg < 0 else "info")})
    tb = t.get("thesis_break", {}) or {}
    if tb.get("any"):
        badges.append({"label": "Thesis flag", "tone": "bad"})

    decision = provisional_lean(t, cfg)
    return {
        "badges": badges,
        "provisional_lean": decision["lean"],
        "drivers": decision["drivers"],
        # back-compat aliases for existing consumers:
        "pile_points": decision["drivers"]["pile"],
        "trim_points": decision["drivers"]["deterioration"],
    }


VALID_HELD_LEANS = {"pile_on", "hold", "trim", "exit"}
VALID_NOT_HELD_LEANS = {"watch", "hold"}


def validate_leans(snap: dict[str, Any]) -> dict[str, Any]:
    """Enforce the action vocabulary on every ticker row (in place; returns snap).

    Every tracked name is held (the user keeps ~$200 in anything worth watching), so
    `watch` is never a valid call on a held name — the routine once used it to demote
    a quant trim into a non-action label, silently. Coercions are VISIBLE
    (`lean_coerced_from` / `lean_rejected`), never silent; a None lean (pre-narrative)
    is left alone (the board falls back to the provisional lean).
    Runs post-merge in both the pipeline and the enrich step, so carried-forward bad
    leans heal without waiting on the LLM.
    """
    for row in snap.get("tickers", []):
        pos = row.get("position") or {}
        held = bool(pos.get("held")) and (pos.get("shares") or 0) > 0
        lean = row.get("final_lean")
        if lean is None:
            continue
        if held and lean == "watch":
            row["final_lean"] = "hold"
            row["lean_coerced_from"] = "watch"
        elif held and lean not in VALID_HELD_LEANS:
            row["final_lean"] = (row.get("signals") or {}).get("provisional_lean") or "hold"
            row["lean_rejected"] = lean
        elif not held and lean not in VALID_NOT_HELD_LEANS:
            row["final_lean"] = "watch"
            row["lean_coerced_from"] = lean
    return snap


# Metric keys this engine references — guarded against metrics.REGISTRY in tests.
REFERENCED_KEYS = {
    "trend", "ma_cross", "rsi14", "dist_sma20_pct", "rs_20d", "days_to_earnings",
    "revenue_growth_yoy", "eps_growth_yoy",
    "tb_revenue_qoq_drop", "tb_margin_compression", "tb_repeated_eps_miss",
}


def provisional_lean(t: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """The transparent rule layer (plan §4). Returns {lean, drivers}.

    Quant actions: watch (not held) · trim (deterioration confluence) · pile_on
    (strength + room) · hold (default / "don't chase").

    The quant layer CAPS AT `trim` — it never emits `exit`. `exit` is the LLM's
    escalation when it judges a *confirmed* break (weighing news, guidance, severity,
    persistence). This prevents a couple of correlated single-quarter flags from
    mechanically manufacturing an exit.

    INVARIANTS:
    - Position weight / size is NEVER read here. Deterioration drives trim, never size.
    - A *single* mild negative → hold (needs a confluence of ≥2 distinct deterioration
      dimensions to trim). Overbought / extended → hold ("don't chase"), never trim.
    """
    s = cfg.get("signals", {})
    tech = t.get("technicals", {}) or {}
    pos = t.get("position", {}) or {}
    earn = t.get("earnings", {}) or {}
    fund = t.get("fundamentals", {}) or {}
    tb = t.get("thesis_break", {}) or {}
    rs = t.get("relative_strength", {}) or {}

    held = bool(pos.get("held")) and (pos.get("shares") or 0) > 0

    rsi = tech.get("rsi14")
    overbought = rsi is not None and rsi >= s.get("rsi_overbought", 70)
    d20 = tech.get("dist_sma20_pct")
    extended = d20 is not None and d20 >= s.get("extended_above_sma20_pct", 12.0)
    days = earn.get("days_until_next")
    into_earnings = days is not None and 0 <= days <= 1

    trend = tech.get("trend")
    ma_cross = tech.get("ma_cross")
    rs20 = rs.get("rs20d")
    rev_yoy = fund.get("revenue_yoy")
    eps_yoy = fund.get("eps_yoy")

    # Deterioration as DISTINCT dimensions (each counted once — correlated revenue
    # signals don't double-count, per review). These are the only things that trim.
    revenue_weakening = (rev_yoy is not None and rev_yoy < 0) or (tb.get("revenue_qoq_drop") is True)
    earnings_quality = (eps_yoy is not None and eps_yoy < 0) or (tb.get("repeated_eps_miss") is True)
    det = {
        "downtrend": (trend == "downtrend") or (ma_cross == "death_cross"),
        "negative_rel_strength": rs20 is not None and rs20 < 0,
        "revenue_weakening": revenue_weakening,
        "margin_compression": tb.get("margin_compression") is True,
        "earnings_quality_deteriorating": earnings_quality,
    }
    det_true = [k for k, v in det.items() if v]

    # strength + room
    strong = (trend == "uptrend") or (ma_cross in ("golden_cross", "above"))
    rs_ok = (rs20 is None) or (rs20 >= 0)
    room = (not overbought) and (not extended) and (not into_earnings) and (len(det_true) == 0)

    pile: list[str] = []
    if trend == "uptrend":
        pile.append("uptrend")
    if ma_cross == "golden_cross":
        pile.append("golden cross")
    if rs20 is not None and rs20 > 0:
        pile.append("leading the market (positive RS)")
    if rev_yoy is not None and rev_yoy >= 15:
        pile.append(f"revenue +{rev_yoy:.0f}% YoY")

    blocks: list[str] = []
    if overbought:
        blocks.append(f"overbought (RSI {rsi:.0f})")
    if extended:
        blocks.append(f"extended {d20:.0f}% above 20d MA")
    if into_earnings:
        blocks.append("reports within a day (event risk)")

    # ── truth table (order matters; quant caps at trim — LLM owns exit) ──
    if not held:
        lean = "watch"
    elif len(det_true) >= 2:
        lean = "trim"          # deterioration confluence (LLM may escalate to exit)
    elif strong and rs_ok and room:
        lean = "pile_on"
    else:
        lean = "hold"          # incl. overbought/extended = "don't chase", or a single mild negative

    return {"lean": lean, "drivers": {"pile": pile, "deterioration": det_true, "blocks": blocks}}
