"""Quant analytics over a price history: returns, technicals, relative strength."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calendar_utils import returns_window_dates
from . import technicals as ta


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1.0) * 100.0, 2)


def _return_closes(hist: pd.DataFrame) -> pd.Series:
    """Closes for RETURN math: dividend-adjusted ('Adj Close', total return) when
    the feed provides it, else raw Close. Technicals deliberately do NOT use this —
    indicator levels follow the chart, returns follow the money."""
    col = "Adj Close" if "Adj Close" in hist.columns else "Close"
    return hist[col].dropna()


def compute_returns(hist: pd.DataFrame, windows=(1, 5, 20)) -> dict[str, float | None]:
    """Trailing TOTAL returns over N *trading* days, anchored to the last session
    (dividend-adjusted when 'Adj Close' is present)."""
    if hist.empty:
        return {f"r{n}d": None for n in windows}
    closes = _return_closes(hist)
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


# RSI/SMA/MACD/MA-cross/support-resistance/breakout/52w now come from
# tracker.technicals (Wilder RSI etc.) — single source of truth (plan C4).


def _atr(hist: pd.DataFrame, period: int = 14) -> float | None:
    """Wilder-smoothed ATR (same smoothing convention as the RSI), not a plain
    rolling mean — reacts to a volatility spike then decays, as standard."""
    if len(hist) < period + 1:
        return None
    h, l, c = hist["High"], hist["Low"], hist["Close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    return round(float(atr), 2)


def compute_technicals(hist: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if hist.empty:
        return out
    closes = hist["Close"].dropna()
    vols = hist["Volume"].dropna()
    last = float(closes.iloc[-1])
    out["last_close"] = round(last, 2)

    # Moving averages (technicals.sma — single source)
    for win in (20, 50, 200):
        s = ta.sma(closes, win)
        out[f"sma{win}"] = round(s, 2) if s is not None else None
        out[f"dist_sma{win}_pct"] = _pct(last, s)

    # RSI (Wilder), MACD, 50/200 cross — all from technicals
    r = ta.rsi(closes)
    out["rsi14"] = round(r, 1) if r is not None else None
    m = ta.macd(closes)
    out["macd_state"] = m.state if m else None          # bullish_cross | bearish_cross | no_cross
    out["macd_hist"] = round(m.histogram, 3) if m else None
    out["ma_cross"] = ta.sma_cross_state(closes).state   # golden_cross | death_cross | above | below | insufficient

    # ATR (local — technicals has no ATR)
    out["atr14"] = _atr(hist)
    out["atr14_pct"] = _pct_of(out.get("atr14"), last)

    # 52-week range; distance via technicals for parity
    window = closes.tail(252)
    out["high_52w"] = round(float(window.max()), 2)
    out["low_52w"] = round(float(window.min()), 2)
    d52 = ta.dist_from_52w_high(closes)
    out["dist_52w_high_pct"] = round(d52, 2) if d52 is not None else None
    out["dist_52w_low_pct"] = _pct(last, out["low_52w"])

    # Support / resistance — nearest swing pivots (distance + implied level price)
    sup = ta.dist_from_nearest_pivot_below(closes)
    res = ta.dist_from_nearest_pivot_above(closes)
    out["support_dist_pct"] = round(sup, 2) if sup is not None else None
    out["resistance_dist_pct"] = round(res, 2) if res is not None else None
    out["support_price"] = round(last / (1 + sup / 100), 2) if sup is not None else None
    out["resistance_price"] = round(last * (1 + res / 100), 2) if res is not None else None

    # Volume conviction + breakout
    rv = ta.volume_vs_avg(vols, 20)
    out["rel_volume"] = round(rv, 2) if rv is not None else None
    if len(vols) >= 20:
        out["avg_vol_20d"] = int(vols.tail(20).mean())
    bo = ta.breakout_confirmed(closes, vols)
    if bo is not None:
        out["breakout"] = bo.is_breakout
        out["breakout_confirmed"] = bo.is_confirmed

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


RS_MA_WINDOW = 50  # sessions; the daily adaptation of Mansfield's zero line


def _rs_regime(ticker_hist: pd.DataFrame, bench_hist: pd.DataFrame) -> tuple[str | None, float | None]:
    """Mansfield/Weinstein RS regime: the RS line (price ÷ benchmark) vs its own
    50-session MA. Below = 'underperforming' (a persistent lag, the standard
    deterioration read); at/above = 'outperforming'. (None, None) on <51 aligned
    sessions — insufficient history never flags."""
    if ticker_hist.empty or bench_hist.empty:
        return None, None
    t = _return_closes(ticker_hist)
    b = _return_closes(bench_hist)
    ratio = (t / b).dropna()  # index-aligned; non-overlapping dates drop out
    if len(ratio) < RS_MA_WINDOW + 1:
        return None, None
    ma = float(ratio.tail(RS_MA_WINDOW).mean())
    if ma == 0:
        return None, None
    dist = (float(ratio.iloc[-1]) / ma - 1.0) * 100.0
    return ("underperforming" if dist < 0 else "outperforming"), round(dist, 2)


def relative_strength(
    ticker_hist: pd.DataFrame, bench_hist: pd.DataFrame, windows=(5, 20)
) -> dict[str, Any]:
    """Excess return over the benchmark across windows, plus the Mansfield-style
    RS regime (`rs_trend`) the decision engine uses for deterioration."""
    tr = compute_returns(ticker_hist, windows)
    br = compute_returns(bench_hist, windows)
    out: dict[str, Any] = {}
    for n in windows:
        a, b = tr.get(f"r{n}d"), br.get(f"r{n}d")
        out[f"rs{n}d"] = round(a - b, 2) if (a is not None and b is not None) else None
    trend, dist = _rs_regime(ticker_hist, bench_hist)
    out["rs_trend"] = trend
    out["rs_line_ma50_dist_pct"] = dist
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
