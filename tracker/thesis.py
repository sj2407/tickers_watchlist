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
    misses = fund.get("eps_miss_count_last3")
    eps = None if misses is None else (misses >= t["eps_miss_count"])

    flags = {
        "revenue_qoq_drop": rev,
        "margin_compression": margin,
        "repeated_eps_miss": eps,
    }
    flags["any"] = any(v is True for v in flags.values())
    return flags
