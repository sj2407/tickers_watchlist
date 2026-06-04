"""Quant analytics over a price history: returns, technicals, relative strength."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calendar_utils import returns_window_dates


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1.0) * 100.0, 2)


def compute_returns(hist: pd.DataFrame, windows=(1, 5, 20)) -> dict[str, float | None]:
    """Trailing returns over N *trading* days, anchored to the last session."""
    if hist.empty:
        return {f"r{n}d": None for n in windows}
    closes = hist["Close"].dropna()
    if closes.empty:
        return {f"r{n}d": None for n in windows}
    last = float(closes.iloc[-1])
    end = closes.index[-1].date()
    anchors = returns_window_dates(end, windows)
    out: dict[str, float | None] = {}
    for n in windows:
        ref_date = anchors.get(n)
        ref = None
        if ref_date is not None:
            ts = pd.Timestamp(ref_date)
            if ts in closes.index:
                ref = float(closes.loc[ts])
        if ref is None and len(closes) > n:
            ref = float(closes.iloc[-(n + 1)])  # fallback: positional
        out[f"r{n}d"] = _pct(last, ref)
    return out


def _rsi(closes: pd.Series, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return round(100 - (100 / (1 + rs)), 1)


def _atr(hist: pd.DataFrame, period: int = 14) -> float | None:
    if len(hist) < period + 1:
        return None
    h, l, c = hist["High"], hist["Low"], hist["Close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 2)


def compute_technicals(hist: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if hist.empty:
        return out
    closes = hist["Close"].dropna()
    last = float(closes.iloc[-1])
    out["last_close"] = round(last, 2)

    for win in (20, 50, 200):
        if len(closes) >= win:
            sma = float(closes.rolling(win).mean().iloc[-1])
            out[f"sma{win}"] = round(sma, 2)
            out[f"dist_sma{win}_pct"] = _pct(last, sma)
        else:
            out[f"sma{win}"] = None
            out[f"dist_sma{win}_pct"] = None

    out["rsi14"] = _rsi(closes)
    out["atr14"] = _atr(hist)
    out["atr14_pct"] = _pct_of(out.get("atr14"), last)

    # 52-week range from available history (caps at ~1y of sessions)
    window = closes.tail(252)
    hi, lo = float(window.max()), float(window.min())
    out["high_52w"] = round(hi, 2)
    out["low_52w"] = round(lo, 2)
    out["dist_52w_high_pct"] = _pct(last, hi)
    out["dist_52w_low_pct"] = _pct(last, lo)

    # volume conviction
    vol = hist["Volume"].dropna()
    if len(vol) >= 20:
        avg20 = float(vol.tail(20).mean())
        out["avg_vol_20d"] = int(avg20)
        last_vol = float(vol.iloc[-1])
        out["rel_volume"] = round(last_vol / avg20, 2) if avg20 else None

    # trend label
    out["trend"] = _trend_label(out)
    return out


def _pct_of(part: float | None, whole: float | None) -> float | None:
    if part is None or whole in (None, 0):
        return None
    return round(part / whole * 100, 2)


def _trend_label(t: dict[str, Any]) -> str:
    s50, s200 = t.get("sma50"), t.get("sma200")
    last = t.get("last_close")
    if None in (s50, s200, last):
        return "n/a"
    if last > s50 > s200:
        return "uptrend"
    if last < s50 < s200:
        return "downtrend"
    return "mixed"


def relative_strength(
    ticker_hist: pd.DataFrame, bench_hist: pd.DataFrame, windows=(5, 20)
) -> dict[str, float | None]:
    """Excess return of the ticker over the benchmark across windows."""
    tr = compute_returns(ticker_hist, windows)
    br = compute_returns(bench_hist, windows)
    out: dict[str, float | None] = {}
    for n in windows:
        a, b = tr.get(f"r{n}d"), br.get(f"r{n}d")
        out[f"rs{n}d"] = round(a - b, 2) if (a is not None and b is not None) else None
    return out


def position_math(
    holding: dict[str, Any] | None, last_price: float | None, book_value: float | None
) -> dict[str, Any]:
    """Per-position P/L, weight, and since-entry return. None-safe."""
    if not holding or last_price is None:
        return {"held": bool(holding)}
    shares = float(holding.get("shares") or 0)
    cost_basis = holding.get("cost_basis")  # per-share avg cost
    market_value = round(shares * last_price, 2)
    out: dict[str, Any] = {
        "held": True,
        "shares": shares,
        "cost_basis": cost_basis,
        "market_value": market_value,
    }
    if cost_basis:
        invested = shares * float(cost_basis)
        out["invested"] = round(invested, 2)
        out["unrealized_pl"] = round(market_value - invested, 2)
        out["since_entry_pct"] = _pct(last_price, float(cost_basis))
    if book_value:
        out["weight_pct"] = round(market_value / book_value * 100, 2)
    return out
