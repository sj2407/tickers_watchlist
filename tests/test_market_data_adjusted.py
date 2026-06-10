"""P6 gate: returns + relative strength use dividend-adjusted closes (total
return) when yfinance provides 'Adj Close'; technicals/charts/position math stay
on raw Close. The no-Adj-Close fallback must reproduce the P0 characterization
values byte-for-byte — that's the surgical proof.
"""
import numpy as np
import pandas as pd

from tests.synth import price_frame, sessions
from tracker import market_data as md


def _flat_with_dividend(n=120, px=100.0, div_pct=1.0, ex_sessions_ago=3):
    """Price flat at `px` forever; a dividend went ex `ex_sessions_ago` sessions
    ago. Raw Close shows 0% return; Adj Close back-scales pre-ex bars down by the
    dividend, so the TOTAL return over any window crossing the ex-date is +div%."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions()[-n:]])
    close = np.full(n, px)
    adj = close.copy()
    adj[: n - ex_sessions_ago] = px * (1 - div_pct / 100.0)
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close,
                         "Adj Close": adj, "Volume": np.full(n, 1e6)}, index=idx)


def test_returns_are_total_return_when_adjusted_closes_present():
    f = _flat_with_dividend()
    r = md.compute_returns(f)
    # price return is 0%; total return across the ex-date is the 1% dividend
    assert r["r1d"] == 0.0                       # both bars after the ex-date
    assert r["r5d"] == 1.01                      # 100/99 − 1
    assert r["r20d"] == 1.01


def test_without_adj_close_identical_to_characterization_baseline():
    # The exact P0-pinned values — proves the fallback path didn't move.
    t, b = price_frame(1, 100.0), price_frame(2, 300.0)
    assert md.compute_returns(t) == {"r1d": 0.46, "r5d": 1.85, "r20d": 0.43}
    assert md.relative_strength(t, b) == {
        "rs5d": 1.0, "rs20d": 0.23,
        "rs_trend": "outperforming", "rs_line_ma50_dist_pct": 1.45,
    }


def test_mixed_frames_each_side_uses_its_own_best_column():
    tick = _flat_with_dividend()                                   # has Adj Close
    idx = tick.index
    bench = pd.DataFrame({"Open": 200.0, "High": 200.0, "Low": 200.0,
                          "Close": np.full(len(idx), 200.0),
                          "Volume": np.full(len(idx), 1e6)}, index=idx)  # raw only
    rs = md.relative_strength(tick, bench)
    assert rs["rs5d"] == 1.01                    # ticker total-return vs bench price-return
    assert rs["rs20d"] == 1.01


def test_technicals_ignore_adj_close_entirely():
    f = _flat_with_dividend()
    raw_only = f.drop(columns=["Adj Close"])
    assert md.compute_technicals(f) == md.compute_technicals(raw_only)
