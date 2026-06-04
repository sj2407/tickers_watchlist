"""Technical indicators for the checklist's technical layer.

Strict boundary: this module is pure functions over arrays of prices and
volumes. It does NOT open any database, read any file, or import the
network. That keeps it unit-testable without a fixture and keeps the
"DB only in storage.py / refresh.py" rule clean.

Enforced by test_no_technical_function_opens_a_database (AST grep).

Indicators (all from daily closes / volumes):
  • RSI(14)        Wilder's smoothing
  • MACD(12,26,9)  with last-bar crossover state
  • SMA(N)         arithmetic mean; SMA(50)/(200) cross state
  • swing pivots   window-based local extrema + distance to nearest
  • dist_from_52w_high   same formula as analytics/momentum.py
  • volume_vs_avg  current volume / prior-N mean
  • is_breakout / breakout_confirmed   N-bar close-high + volume confirmation

All public functions accept numpy ndarray, pandas Series, or list[float]
inputs. Inputs are assumed to be in chronological order (oldest → newest).
Latest bar is the last element. None returned on insufficient history
(so the checklist layer can flag insufficient_data per-signal).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MACDResult:
    """Latest MACD reading plus state of the most recent crossover."""
    line: float
    signal: float
    histogram: float
    state: str  # bullish_cross | bearish_cross | no_cross


@dataclass
class SMACrossResult:
    sma_50: float | None
    sma_200: float | None
    state: str  # golden_cross | death_cross | above | below | insufficient


@dataclass
class SwingPivot:
    index: int
    price: float
    kind: str  # "high" | "low"


@dataclass
class BreakoutResult:
    is_breakout: bool
    is_confirmed: bool
    volume_ratio: float


# ── input normalization ───────────────────────────────────────────────

def _as_array(x) -> np.ndarray:
    """Coerce list / pandas Series / ndarray to a 1-D float numpy array.
    NaN values are preserved; callers handle them."""
    if isinstance(x, np.ndarray):
        return x.astype(float, copy=False)
    if isinstance(x, pd.Series):
        return x.to_numpy(dtype=float, copy=False)
    return np.asarray(x, dtype=float)


# ── RSI(14) — Wilder ──────────────────────────────────────────────────

def rsi(closes, n: int = 14) -> float | None:
    """Wilder's RSI on the latest bar. None if < n+1 bars.

    Convention for a perfectly flat series (no movement): RSI = 50.
    """
    arr = _as_array(closes)
    if arr.size < n + 1:
        return None

    diffs = np.diff(arr)
    gains = np.where(diffs > 0, diffs, 0.0)
    losses = np.where(diffs < 0, -diffs, 0.0)

    # Wilder initialization: simple average of first n changes
    avg_gain = float(np.mean(gains[:n]))
    avg_loss = float(np.mean(losses[:n]))

    # Wilder smoothing for the remaining bars
    for i in range(n, diffs.size):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n

    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


# ── MACD(12, 26, 9) ───────────────────────────────────────────────────

def _ema(x: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average, seeded with the first SMA(span).
    Returns an array of length len(x); positions before span-1 are NaN."""
    if x.size < span:
        return np.full(x.size, np.nan)
    alpha = 2.0 / (span + 1.0)
    out = np.full(x.size, np.nan)
    out[span - 1] = np.mean(x[:span])
    for i in range(span, x.size):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def macd(
    closes, fast: int = 12, slow: int = 26, signal: int = 9
) -> MACDResult | None:
    arr = _as_array(closes)
    min_needed = slow + signal  # need slow EMA, then signal EMA on top
    if arr.size < min_needed:
        return None

    fast_ema = _ema(arr, fast)
    slow_ema = _ema(arr, slow)
    macd_line = fast_ema - slow_ema

    # Signal line is EMA(signal) of the MACD line — but only over the
    # valid (non-NaN) portion of macd_line.
    macd_valid_from = slow - 1
    if arr.size - macd_valid_from < signal:
        return None
    signal_line = np.full(arr.size, np.nan)
    sig_input = macd_line[macd_valid_from:]
    sig_ema = _ema(sig_input, signal)
    signal_line[macd_valid_from:] = sig_ema

    histogram = macd_line - signal_line

    # Crossover state at the LAST bar (compare hist sign-change with prior bar).
    state = "no_cross"
    if not np.isnan(histogram[-1]) and not np.isnan(histogram[-2]):
        prior = histogram[-2]
        latest = histogram[-1]
        if prior <= 0 < latest:
            state = "bullish_cross"
        elif prior >= 0 > latest:
            state = "bearish_cross"

    return MACDResult(
        line=float(macd_line[-1]),
        signal=float(signal_line[-1]),
        histogram=float(histogram[-1]),
        state=state,
    )


# ── SMA + golden/death cross ──────────────────────────────────────────

def sma(closes, n: int) -> float | None:
    arr = _as_array(closes)
    if arr.size < n or n <= 0:
        return None
    return float(np.mean(arr[-n:]))


def sma_cross_state(closes) -> SMACrossResult:
    """Returns SMA(50), SMA(200), and the state.
    Per convention: 'golden_cross' / 'death_cross' fires only when the
    50/200 lines crossed on the LATEST bar (i.e. the relative sign flipped
    from the prior bar). Otherwise 'above' / 'below'.
    """
    arr = _as_array(closes)
    if arr.size < 200:
        return SMACrossResult(sma_50=None, sma_200=None, state="insufficient")

    sma50_latest = float(np.mean(arr[-50:]))
    sma200_latest = float(np.mean(arr[-200:]))
    # Need the *prior* bar's SMA(50) and SMA(200) to detect a crossover.
    sma50_prior = float(np.mean(arr[-51:-1]))
    sma200_prior = float(np.mean(arr[-201:-1]))

    latest_diff = sma50_latest - sma200_latest
    prior_diff = sma50_prior - sma200_prior

    if latest_diff > 0 and prior_diff <= 0:
        state = "golden_cross"
    elif latest_diff < 0 and prior_diff >= 0:
        state = "death_cross"
    elif latest_diff > 0:
        state = "above"
    elif latest_diff < 0:
        state = "below"
    else:
        # exactly equal — rare; treat as 'above' if the previous regime was below
        state = "above" if prior_diff < 0 else "below"

    return SMACrossResult(sma_50=sma50_latest, sma_200=sma200_latest, state=state)


# ── swing pivots ──────────────────────────────────────────────────────

def _find_pivots(arr: np.ndarray, window: int) -> list[SwingPivot]:
    """A bar at index i is a swing HIGH iff arr[i] is strictly greater than
    every arr[i-window..i-1] AND every arr[i+1..i+window]. Mirror for LOW.

    Edge bars (within `window` of either end) are skipped: we can't confirm
    a pivot at the very last bar without future data, by definition.
    """
    if arr.size < 2 * window + 1:
        return []
    out: list[SwingPivot] = []
    for i in range(window, arr.size - window):
        left = arr[i - window: i]
        right = arr[i + 1: i + window + 1]
        v = arr[i]
        if v > left.max() and v > right.max():
            out.append(SwingPivot(index=i, price=float(v), kind="high"))
        elif v < left.min() and v < right.min():
            out.append(SwingPivot(index=i, price=float(v), kind="low"))
    return out


def swing_pivots(
    closes, window: int = 5, max_per_side: int = 5
) -> list[SwingPivot]:
    """Return the most recent ≤max_per_side highs and ≤max_per_side lows."""
    arr = _as_array(closes)
    all_pivots = _find_pivots(arr, window)
    # Most recent first
    highs = [p for p in all_pivots if p.kind == "high"][::-1][:max_per_side][::-1]
    lows = [p for p in all_pivots if p.kind == "low"][::-1][:max_per_side][::-1]
    return highs + lows


def dist_from_nearest_pivot_below(closes, window: int = 5) -> float | None:
    """Percent distance from latest close to the highest swing LOW below it.
    Returns positive percent (close - pivot) / pivot * 100. None if none below."""
    arr = _as_array(closes)
    if arr.size == 0:
        return None
    latest = float(arr[-1])
    pivots = _find_pivots(arr, window)
    lows_below = [p for p in pivots if p.kind == "low" and p.price < latest]
    if not lows_below:
        return None
    nearest = max(lows_below, key=lambda p: p.price)
    return (latest - nearest.price) / nearest.price * 100.0


def dist_from_nearest_pivot_above(closes, window: int = 5) -> float | None:
    """Percent distance from latest close to the lowest swing HIGH above it.
    Returns positive percent (pivot - close) / close * 100. None if none above."""
    arr = _as_array(closes)
    if arr.size == 0:
        return None
    latest = float(arr[-1])
    pivots = _find_pivots(arr, window)
    highs_above = [p for p in pivots if p.kind == "high" and p.price > latest]
    if not highs_above:
        return None
    nearest = min(highs_above, key=lambda p: p.price)
    return (nearest.price - latest) / latest * 100.0


# ── dist_from_52w_high (parity with analytics/momentum.py) ────────────

def dist_from_52w_high(closes) -> float | None:
    """Matches analytics/momentum.py: (latest / max(last 252) - 1) * 100.
    Negative (or zero) — closer to 0 = stronger.
    If fewer than 252 bars, uses what's available (does NOT return None)."""
    arr = _as_array(closes)
    if arr.size == 0:
        return None
    window = arr[-252:] if arr.size >= 252 else arr
    hi = float(np.max(window))
    if hi <= 0:
        return None
    latest = float(arr[-1])
    return (latest / hi - 1.0) * 100.0


# ── volume + breakout ─────────────────────────────────────────────────

def volume_vs_avg(volumes, n: int = 20) -> float | None:
    """latest_volume / mean(prior n volumes). None if insufficient."""
    arr = _as_array(volumes)
    if arr.size < n + 1:
        return None
    prior = arr[-n - 1: -1]
    mean_prior = float(np.mean(prior))
    if mean_prior == 0:
        return None
    return float(arr[-1]) / mean_prior


def is_breakout(closes, n: int = 20) -> bool | None:
    """True if latest close > max(prior n closes)."""
    arr = _as_array(closes)
    if arr.size < n + 1:
        return None
    prior_max = float(np.max(arr[-n - 1: -1]))
    return bool(float(arr[-1]) > prior_max)


def breakout_confirmed(
    closes, volumes, n: int = 20, vol_threshold: float = 1.5
) -> BreakoutResult | None:
    """Combined: breakout AND volume_ratio ≥ vol_threshold."""
    closes_arr = _as_array(closes)
    volumes_arr = _as_array(volumes)
    if closes_arr.size < n + 1 or volumes_arr.size < n + 1:
        return None
    brk = is_breakout(closes_arr, n=n)
    ratio = volume_vs_avg(volumes_arr, n=n)
    if brk is None or ratio is None:
        return None
    return BreakoutResult(
        is_breakout=brk,
        is_confirmed=brk and ratio >= vol_threshold,
        volume_ratio=float(ratio),
    )
