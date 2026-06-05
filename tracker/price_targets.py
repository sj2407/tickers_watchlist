"""Analyst price targets (low / median / mean / high + # analysts) from yfinance.

Free, and covers US names and ADRs alike. SUMMARY STATS ONLY: the per-analyst raw
targets needed for true quartiles/outliers are not on the current data plans
(FMP's per-analyst endpoint is 402/404 on this tier), so the web visual draws a
faithful range strip from these numbers rather than inventing percentiles.
"""
from __future__ import annotations

from typing import Any

import yfinance as yf


def _pos(x: Any) -> float | None:
    """Round to 2dp, or None for missing / NaN / non-positive."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v <= 0:  # NaN or non-positive → treat as missing
        return None
    return round(v, 2)


def fetch_target(ticker: str) -> dict[str, Any] | None:
    """Return {low, median, mean, high, num_analysts, source} or None if unavailable.

    Returns None unless we have a real low<=high range and at least one central
    estimate (median or mean), so the web side never has to draw a degenerate bar.
    """
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return None

    low = _pos(info.get("targetLowPrice"))
    median = _pos(info.get("targetMedianPrice"))
    mean = _pos(info.get("targetMeanPrice"))
    high = _pos(info.get("targetHighPrice"))
    try:
        n = int(info.get("numberOfAnalystOpinions") or 0) or None
    except (TypeError, ValueError):
        n = None

    if low is None or high is None or high < low or (mean is None and median is None):
        return None

    return {
        "low": low,
        "median": median,
        "mean": mean,
        "high": high,
        "num_analysts": n,
        "source": "yfinance",
    }
