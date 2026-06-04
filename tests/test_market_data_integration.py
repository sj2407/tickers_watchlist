"""P1 gate: technicals are wired into compute_technicals via the single
`tracker.technicals` source (C4 guard), and the integrated output is well-formed.
Offline — builds a synthetic OHLCV frame, no network.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from tracker import market_data as md


def _synthetic_hist(n: int = 260) -> pd.DataFrame:
    # gently rising series with noise so indicators are computable
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    base = np.linspace(100, 160, n) + np.sin(np.linspace(0, 12, n)) * 4
    close = base
    high = close + 1.5
    low = close - 1.5
    openp = close - 0.3
    vol = np.full(n, 1_000_000.0)
    vol[-1] = 2_500_000.0  # a volume spike on the last bar
    return pd.DataFrame(
        {"Open": openp, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )


# ── C4: single RSI implementation ──────────────────────────────────────

def test_market_data_has_no_duplicate_rsi():
    src = (Path(__file__).resolve().parents[1] / "tracker" / "market_data.py").read_text()
    assert "def _rsi" not in src, "duplicate RSI in market_data — must use technicals.rsi"
    assert "technicals as ta" in src, "market_data must import the technicals module"


def test_rsi_matches_technicals_exactly():
    """The pipeline's RSI is the Wilder RSI from technicals (no divergent math)."""
    from tracker import technicals as ta

    hist = _synthetic_hist()
    out = md.compute_technicals(hist)
    expected = ta.rsi(hist["Close"].dropna())
    assert out["rsi14"] == round(expected, 1)


# ── integrated output shape ─────────────────────────────────────────────

def test_compute_technicals_has_new_fields():
    out = md.compute_technicals(_synthetic_hist())
    for key in (
        "rsi14", "macd_state", "macd_hist", "ma_cross",
        "sma20", "sma50", "sma200", "dist_sma50_pct",
        "atr14", "atr14_pct", "dist_52w_high_pct",
        "support_dist_pct", "resistance_dist_pct", "rel_volume", "trend",
    ):
        assert key in out, f"missing technical field: {key}"
    assert out["ma_cross"] in {"golden_cross", "death_cross", "above", "below", "insufficient"}
    assert out["macd_state"] in {"bullish_cross", "bearish_cross", "no_cross", None}


def test_empty_history_is_safe():
    assert md.compute_technicals(pd.DataFrame()) == {}
