"""Phase 3 — technical indicators (pure functions, no DB).

Tests are the CONTRACT for src/checklist/technicals.py. Each indicator
is unit-tested against a hand-built series with a known answer (golden
values) so the math is verifiable without depending on any external
TA library.

The isolation guard (test_no_technical_function_opens_a_database)
enforces the pure-function boundary: this module must not import
sqlite3, must not read files, must not touch the cache. The reviewer
explicitly flagged this — keep it locked.
"""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tracker import technicals as ta


# ── helpers ────────────────────────────────────────────────────────────

def _arr(values) -> np.ndarray:
    return np.array(values, dtype=float)


def _linear_up(n: int, start: float = 100.0, step: float = 1.0) -> np.ndarray:
    return _arr([start + i * step for i in range(n)])


def _linear_down(n: int, start: float = 200.0, step: float = 1.0) -> np.ndarray:
    return _arr([start - i * step for i in range(n)])


# ── Section A: RSI(14) ────────────────────────────────────────────────

class TestRSI:
    def test_only_gains_returns_100(self):
        """Monotone increase → avg_loss = 0 → RSI = 100."""
        assert ta.rsi(_linear_up(30)) == pytest.approx(100.0)

    def test_only_losses_returns_0(self):
        """Monotone decrease → avg_gain = 0 → RSI = 0."""
        assert ta.rsi(_linear_down(30)) == pytest.approx(0.0)

    def test_flat_series_returns_50(self):
        """No change at all is undefined; convention is 50 (neutral)."""
        assert ta.rsi(_arr([100.0] * 30)) == pytest.approx(50.0)

    def test_insufficient_history_returns_none(self):
        """RSI(14) needs ≥ 15 bars (1 baseline + 14 changes)."""
        assert ta.rsi(_arr([100.0, 101.0, 102.0])) is None
        assert ta.rsi(_arr([100.0] * 14)) is None

    def test_15_bars_is_minimum_sufficient(self):
        """Exactly 15 bars → first valid RSI value."""
        v = ta.rsi(_linear_up(15))
        assert v == pytest.approx(100.0)

    def test_accepts_pandas_series_and_list(self):
        up = _linear_up(20)
        v_np = ta.rsi(up)
        v_pd = ta.rsi(pd.Series(up))
        v_list = ta.rsi(up.tolist())
        assert v_np == v_pd == v_list

    def test_handles_mixed_series_with_known_wilder_value(self):
        """A modest mixed series. Computed against the standard Wilder
        formula; locks the implementation to a specific arithmetic, so
        a future refactor can't silently change RSI semantics."""
        # 15 bars: alternating +2/-1 changes after seed 100.0
        # bar diffs: +2, -1, +2, -1, +2, -1, +2, -1, +2, -1, +2, -1, +2, -1
        # gains sum = 7*2 = 14; losses sum = 7*1 = 7
        # initial avg_gain = 14/14 = 1.0; initial avg_loss = 7/14 = 0.5
        # RS = 2.0; RSI = 100 - 100/3 = 66.666...
        closes = [100.0]
        for _ in range(7):
            closes.append(closes[-1] + 2)
            closes.append(closes[-1] - 1)
        # 15 closes, 14 changes
        v = ta.rsi(_arr(closes))
        assert v == pytest.approx(66.6667, abs=1e-3), \
            f"RSI mismatch: got {v}"


# ── Section B: MACD ───────────────────────────────────────────────────

class TestMACD:
    def test_strictly_rising_series_has_positive_line(self):
        """Monotone-up prices → fast EMA leads slow EMA → MACD line > 0."""
        result = ta.macd(_linear_up(60))
        assert result is not None
        assert result.line > 0

    def test_strictly_falling_series_has_negative_line(self):
        result = ta.macd(_linear_down(60))
        assert result is not None
        assert result.line < 0

    def test_histogram_equals_line_minus_signal(self):
        result = ta.macd(_linear_up(60))
        assert result.histogram == pytest.approx(result.line - result.signal)

    def test_returns_line_signal_histogram_and_state(self):
        result = ta.macd(_linear_up(60))
        assert all(hasattr(result, f) for f in ("line", "signal", "histogram", "state"))

    def test_bullish_cross_detected_on_uptrend_after_flat(self):
        """Flat-then-rising → MACD line crosses signal line UP at the inflection."""
        flat = [100.0] * 40
        rising = [100.0 + 2 * i for i in range(1, 25)]
        closes = _arr(flat + rising)
        result = ta.macd(closes)
        # The latest 1-2 bars should show bullish_cross or no_cross w/ line>signal
        assert result.state in {"bullish_cross", "no_cross"}
        assert result.line > result.signal  # rising, line should be above signal

    def test_bearish_cross_detected_on_downtrend_after_flat(self):
        flat = [100.0] * 40
        falling = [100.0 - 2 * i for i in range(1, 25)]
        result = ta.macd(_arr(flat + falling))
        assert result.state in {"bearish_cross", "no_cross"}
        assert result.line < result.signal

    def test_insufficient_history_returns_none(self):
        """Need slow + signal = 26 + 9 = 35 bars minimum."""
        assert ta.macd(_arr([100.0] * 30)) is None

    def test_accepts_pandas_series(self):
        up = _linear_up(60)
        a = ta.macd(up)
        b = ta.macd(pd.Series(up))
        assert a.line == pytest.approx(b.line)


# ── Section C: SMA + cross state ──────────────────────────────────────

class TestSMA:
    def test_sma_50_equals_arithmetic_mean_of_last_50(self):
        # 50 ones, then 50 twos → SMA(50) of full series = 2.0 (last 50 are all 2)
        closes = _arr([1.0] * 50 + [2.0] * 50)
        assert ta.sma(closes, 50) == pytest.approx(2.0)

    def test_sma_returns_none_when_insufficient(self):
        assert ta.sma(_arr([1.0, 2.0, 3.0]), 50) is None

    def test_sma_accepts_list(self):
        assert ta.sma([1.0] * 50, 50) == pytest.approx(1.0)

    def test_sma_cross_state_above_steady(self):
        """50 has been above 200 for a while — last bar state is 'above',
        no fresh crossover."""
        # Build series where SMA(50) > SMA(200) throughout the lookback.
        # Use a long uptrend; SMA(50) lags less than SMA(200), so 50 > 200.
        closes = _linear_up(250, start=50, step=1.0)
        result = ta.sma_cross_state(closes)
        assert result.sma_50 is not None and result.sma_200 is not None
        assert result.state == "above", f"expected above, got {result.state}"

    def test_sma_cross_state_below_steady(self):
        closes = _linear_down(250, start=300, step=1.0)
        result = ta.sma_cross_state(closes)
        assert result.state == "below", f"expected below, got {result.state}"

    def test_sma_cross_state_golden_cross_on_transition(self):
        """Long downtrend then sharp uptrend → fresh 50-over-200 crossover
        at some recent bar. State should be 'golden_cross' if the crossover
        is the LATEST bar's flip; otherwise 'above'."""
        # 200 bars of decline (so SMA(50) is well below SMA(200)),
        # then sharp rally until SMA(50) crosses above SMA(200).
        decline = list(_linear_down(200, start=400, step=1.0))  # ends near 200
        rally = [decline[-1] + 8 * i for i in range(1, 200)]    # sharp rise
        result = ta.sma_cross_state(_arr(decline + rally))
        # After a long enough rally SMA(50) must be above SMA(200).
        # The exact bar of crossover depends on math; accept golden_cross
        # OR above (i.e. crossed and now steady-above).
        assert result.state in {"golden_cross", "above"}

    def test_sma_cross_state_death_cross_on_transition(self):
        rise = list(_linear_up(200, start=100, step=1.0))       # ends near 300
        fall = [rise[-1] - 8 * i for i in range(1, 200)]
        result = ta.sma_cross_state(_arr(rise + fall))
        assert result.state in {"death_cross", "below"}

    def test_sma_cross_state_insufficient_when_under_200_bars(self):
        result = ta.sma_cross_state(_arr([100.0] * 150))
        assert result.state == "insufficient"


# ── Section D: swing pivots + distances ───────────────────────────────

class TestSwingPivots:
    def test_detects_local_high(self):
        """A clear peak in the middle of a window should be detected."""
        closes = _arr([1, 2, 3, 4, 5, 4, 3, 2, 1] + [0.5] * 20)
        pivots = ta.swing_pivots(closes, window=4)
        highs = [p for p in pivots if p.kind == "high"]
        # The 5 (index 4) is a window-4 local high
        assert any(p.index == 4 and p.price == 5.0 for p in highs), \
            f"missed clear high at index 4: pivots={pivots}"

    def test_detects_local_low(self):
        closes = _arr([5, 4, 3, 2, 1, 2, 3, 4, 5] + [10.0] * 20)
        pivots = ta.swing_pivots(closes, window=4)
        lows = [p for p in pivots if p.kind == "low"]
        assert any(p.index == 4 and p.price == 1.0 for p in lows)

    def test_caps_at_max_per_side(self):
        """Many oscillations: returned list should be ≤ 2 × max_per_side."""
        n = 80
        # zigzag every 5 bars
        closes = _arr([10 + (i % 10) for i in range(n)])
        pivots = ta.swing_pivots(closes, window=2, max_per_side=3)
        highs = [p for p in pivots if p.kind == "high"]
        lows = [p for p in pivots if p.kind == "low"]
        assert len(highs) <= 3
        assert len(lows) <= 3

    def test_dist_from_nearest_pivot_below_is_positive_percent(self):
        # Series: low @ 50, then climb to 60 → distance ≈ (60-50)/50 * 100 = 20%
        closes = _arr([55, 52, 50, 51, 53, 55, 57, 59, 60] + [60] * 20)
        d = ta.dist_from_nearest_pivot_below(closes, window=2)
        assert d is not None and d > 0
        # Latest close is 60, nearest pivot low is 50 → 20%
        assert d == pytest.approx(20.0, abs=1.0)

    def test_dist_from_nearest_pivot_above_is_positive_percent(self):
        # Series: rise to 70 then dip to 60. Distance to peak above = (70-60)/60*100 ≈ 16.67%
        closes = _arr([60, 62, 65, 68, 70, 68, 65, 62, 60] + [60] * 20)
        d = ta.dist_from_nearest_pivot_above(closes, window=2)
        assert d is not None and d > 0
        assert d == pytest.approx(16.67, abs=1.0)

    def test_no_pivot_below_returns_none(self):
        """Strictly monotonic up series has no swing low → None."""
        d = ta.dist_from_nearest_pivot_below(_linear_up(30), window=4)
        assert d is None


# ── Section E: dist_from_52w_high (regression vs momentum.py) ─────────

class TestDistFrom52wHigh:
    def test_matches_momentum_py_formula(self):
        """Same formula as analytics/momentum.py:
           (latest / max(last 252) - 1) * 100
        Locks the math so the dashboard and the watchlist agree."""
        closes = _arr([100 + i for i in range(252)])  # peaks at 351 last bar
        # Latest = 351, max of last 252 = 351 → distance = 0
        d = ta.dist_from_52w_high(closes)
        assert d == pytest.approx(0.0)

    def test_below_high_returns_negative(self):
        # 252 bars rising to 200, then a drop to 180
        closes = _arr(list(range(100, 100 + 252)) + [180.0])
        # Take last 252: indices 1..252 in our list. Max = 351, latest = 180.
        d = ta.dist_from_52w_high(closes)
        assert d is not None and d < 0

    def test_insufficient_history_uses_available(self):
        """Per momentum.py semantics: if < 252 bars, use what's available
        (don't return None; just take the full series)."""
        closes = _arr([100, 110, 105, 90])
        # max = 110, latest = 90 → distance ≈ (90/110 - 1)*100 ≈ -18.18%
        d = ta.dist_from_52w_high(closes)
        assert d == pytest.approx(-18.18, abs=0.05)


# ── Section F: volume + breakout ──────────────────────────────────────

class TestVolumeAndBreakout:
    def test_volume_vs_avg_returns_ratio(self):
        vols = _arr([1000.0] * 20 + [2000.0])
        # latest = 2000, avg(last 20 prior) = 1000 → ratio = 2.0
        assert ta.volume_vs_avg(vols, n=20) == pytest.approx(2.0)

    def test_volume_vs_avg_insufficient_returns_none(self):
        assert ta.volume_vs_avg(_arr([1000.0, 1100.0]), n=20) is None

    def test_is_breakout_fires_when_close_above_20day_max(self):
        closes = _arr(list(range(80, 100)) + [101.0])
        # Last 20 prior closes go 80..99, max = 99; latest = 101 > 99 → breakout
        assert ta.is_breakout(closes, n=20) is True

    def test_is_breakout_false_inside_range(self):
        closes = _arr(list(range(80, 100)) + [98.0])
        # latest = 98 < 99 → not a breakout
        assert ta.is_breakout(closes, n=20) is False

    def test_confirmed_breakout_requires_volume_threshold(self):
        """is_confirmed True only when BOTH:
           close >= prior-20 max AND volume >= 1.5x avg(prior 20)."""
        closes = _arr(list(range(80, 100)) + [101.0])
        # Case A: breakout + 2x volume → confirmed
        vols_high = _arr([1000.0] * 20 + [2000.0])
        a = ta.breakout_confirmed(closes, vols_high, n=20, vol_threshold=1.5)
        assert a.is_breakout is True
        assert a.is_confirmed is True
        assert a.volume_ratio == pytest.approx(2.0)
        # Case B: breakout but flat volume → NOT confirmed
        vols_flat = _arr([1000.0] * 20 + [1000.0])
        b = ta.breakout_confirmed(closes, vols_flat, n=20, vol_threshold=1.5)
        assert b.is_breakout is True
        assert b.is_confirmed is False

    def test_no_breakout_no_confirmation(self):
        closes = _arr(list(range(80, 100)) + [95.0])
        vols = _arr([1000.0] * 20 + [3000.0])  # huge volume but not a breakout
        result = ta.breakout_confirmed(closes, vols, n=20, vol_threshold=1.5)
        assert result.is_breakout is False
        assert result.is_confirmed is False


# ── Section G: isolation guards (regression for reviewer R2 P2) ───────

class TestIsolation:
    """The technicals module must remain pure: no DB, no filesystem, no
    network. Reviewer R2 P2 specifically flagged this — keep it locked."""

    def test_no_technical_function_opens_a_database(self):
        """AST grep: technicals.py must not import sqlite3 or `from .. import cache`
        and must not call cache.connect / open() / Path() on a file."""
        path = Path(__file__).resolve().parents[1] / "tracker" / "technicals.py"
        tree = ast.parse(path.read_text())

        banned_imports = {"sqlite3"}
        banned_attr_chains = {("cache", "connect"), ("cache", "init_db")}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in banned_imports, \
                        f"technicals.py must not import {alias.name}"
            if isinstance(node, ast.ImportFrom):
                if node.module and "cache" in node.module:
                    raise AssertionError(
                        f"technicals.py must not import from cache; got {node.module}"
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # walk attribute chain
                parts = []
                cur = node.func
                while isinstance(cur, ast.Attribute):
                    parts.insert(0, cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.insert(0, cur.id)
                if tuple(parts[-2:]) in banned_attr_chains:
                    raise AssertionError(
                        f"technicals.py must not call {'.'.join(parts)}"
                    )

    def test_no_file_operations(self):
        """No open(), no Path().read_text(), no os.path."""
        path = Path(__file__).resolve().parents[1] / "tracker" / "technicals.py"
        src = path.read_text()
        for banned in ("open(", "read_text", "import os", "Path("):
            assert banned not in src, \
                f"technicals.py contains banned construct: {banned!r}"

    def test_module_only_imports_stdlib_and_dataclasses(self):
        """No pandas/numpy import at module level is fine — but if present,
        only stdlib + numpy + pandas + dataclasses are allowed."""
        path = Path(__file__).resolve().parents[1] / "tracker" / "technicals.py"
        tree = ast.parse(path.read_text())
        allowed = {
            "numpy", "pandas",                # math libs
            "dataclasses", "typing",          # type hints
            "math", "statistics", "__future__",  # stdlib math
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    assert base in allowed, \
                        f"unexpected import: {alias.name}"
            if isinstance(node, ast.ImportFrom):
                base = (node.module or "").split(".")[0]
                if base and base not in allowed:
                    raise AssertionError(f"unexpected import: from {node.module}")
