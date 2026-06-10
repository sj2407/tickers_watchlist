"""Quantified thesis-break flags — the only quant signals that can push a held
name toward trim/exit. Everything is None-safe: missing fundamentals yield
`None` (insufficient), NEVER a false `True`.

These *support* the LLM's qualitative thesis-break (guidance cut, catalyst
failure) — they don't replace it. The LLM weighs severity and can escalate or
de-escalate. Position size is never an input here.
"""
from __future__ import annotations

from typing import Any

DEFAULTS = {
    "revenue_qoq_drop_pct": -5.0,    # revenue fell ≥5% sequentially
    "margin_qoq_drop_pp": -2.0,      # gross margin fell ≥2pp sequentially
    "eps_miss_count": 2,             # ≥2 of last 3 quarters missed
    # A SMALL sequential margin dip is normal noise for a hypergrowth name (capacity
    # ramp, mix) — suppress it when YoY revenue growth is strong. But a SEVERE collapse
    # (≤ margin_severe_pp) is real deterioration and is NEVER suppressed.
    "margin_suppress_if_rev_yoy_above": 30.0,
    "margin_severe_pp": -5.0,
}


def thesis_break_flags(fund: dict[str, Any] | None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return {revenue_qoq_drop, margin_compression, repeated_eps_miss, any} where
    each flag is True/False/None (None = insufficient data). `any` is True iff at
    least one flag is True."""
    t = {**DEFAULTS, **((cfg or {}).get("thesis") or {})}
    fund = fund or {}

    def flag_lte(value, threshold):
        return None if value is None else (value <= threshold)

    rev = flag_lte(fund.get("revenue_qoq_pct"), t["revenue_qoq_drop_pct"])
    margin = flag_lte(fund.get("gross_margin_qoq_pp"), t["margin_qoq_drop_pp"])
    gm_qoq = fund.get("gross_margin_qoq_pp")
    severe = None if gm_qoq is None else (gm_qoq <= t["margin_severe_pp"])

    # Seasonality guard (P4): a MILD sequential dip only flags when the margin is
    # also down vs the SAME QUARTER LAST YEAR (gross_margin_yoy_pp ≤ 0) — many of
    # these names have seasonal mix swings that a naive QoQ misreads. No YoY
    # history → insufficient corroboration → None, never a flag. A SEVERE collapse
    # (≤ margin_severe_pp) flags regardless of seasonality.
    if margin is True and severe is not True:
        gm_yoy = fund.get("gross_margin_yoy_pp")
        if gm_yoy is None:
            margin = None
        elif gm_yoy > 0:
            margin = False
    # Suppress only MILD margin compression for strong-growth names (noise). A severe
    # collapse always flags, regardless of growth.
    rev_yoy = fund.get("revenue_yoy")
    if (margin is True and severe is not True
            and rev_yoy is not None and rev_yoy >= t["margin_suppress_if_rev_yoy_above"]):
        margin = False
    misses = fund.get("eps_miss_count_last3")
    eps = None if misses is None else (misses >= t["eps_miss_count"])

    flags = {
        "revenue_qoq_drop": rev,
        "margin_compression": margin,
        "repeated_eps_miss": eps,
    }
    flags["any"] = any(v is True for v in flags.values())
    # Severity qualifier for the decision engine (hard vs soft dimension, P4b).
    # Deliberately OUTSIDE 'any' — it qualifies margin_compression, it doesn't
    # independently assert a break.
    flags["margin_severe"] = severe
    return flags
