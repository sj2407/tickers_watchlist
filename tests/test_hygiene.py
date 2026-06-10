"""P9 gate: config drift closed (RSI 30 per the resolved PLAN-v2 decision #1,
dead keys removed) + ATR on Wilder smoothing like the RSI."""
import numpy as np
import pandas as pd
import pytest

from tracker import signals
from tracker.config import load_config
from tracker import market_data as md


def test_rsi_oversold_band_is_30():
    cfg = load_config()
    assert cfg["signals"]["rsi_oversold"] == 30


def test_dead_config_keys_removed():
    cfg = load_config()
    assert "position_weight_cap_pct" not in cfg["signals"]  # size never trims — key was a lie
    assert "growth_benchmark" not in cfg                     # never read anywhere


def test_rsi_badge_boundary_at_30():
    cfg = load_config()

    def badge(rsi):
        row = {"technicals": {"rsi14": rsi}, "position": {}, "earnings": {},
               "fundamentals": {}, "thesis_break": {}, "relative_strength": {}}
        out = signals.build_signals(row, cfg)
        return any(b["label"].startswith("RSI") for b in out["badges"])

    assert badge(30.0) is True    # at the band (<=)
    assert badge(31.0) is False   # inside neutral
    assert badge(70.0) is True    # overbought side unchanged


def test_atr_is_wilder_smoothed():
    # 15 bars with constant true range 2, then one bar with TR 4:
    # Wilder: 2 + (4-2)/14 = 2.142857 -> 2.14. A plain rolling mean would give
    # mean(2*13, 4) = 2.142857 only by coincidence of window... assert the exact
    # recursive path with a second jump where they genuinely diverge.
    n = 16
    close = np.full(n, 100.0)
    high = close + 1.0
    low = close - 1.0
    high[-1], low[-1] = 102.0, 98.0  # TR 4 on the last bar
    f = pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close,
                      "Volume": np.full(n, 1e6)})
    assert md._atr(f) == pytest.approx(2.14, abs=0.005)

    # two consecutive jumps: Wilder compounds (2 -> 2.1429 -> 2.2755);
    # a 14-bar rolling mean would say mean(12*2, 4, 4) = 2.2857.
    high2, low2 = high.copy(), low.copy()
    high2[-2], low2[-2] = 102.0, 98.0
    f2 = pd.DataFrame({"Open": close, "High": high2, "Low": low2, "Close": close,
                       "Volume": np.full(n, 1e6)})
    assert md._atr(f2) == pytest.approx(2.28, abs=0.005)
    assert md._atr(f2) != pytest.approx(2.2857, abs=0.001)  # NOT the rolling mean
