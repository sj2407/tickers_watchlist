"""P0 characterization: pins compute_returns / relative_strength behavior BEFORE
P6 switches them to dividend-adjusted closes. These exact values are the regression
baseline: P6's no-Adj-Close fallback path must reproduce them bit-for-bit.

Values are hard-coded from a one-off run against the synthetic frames (tests/synth.py)
— they are facts about today's code, not derived in-test (no mirrored math).
"""
import pytest

from tests.synth import price_frame
from tracker import market_data as md


@pytest.fixture(scope="module")
def ticker_hist():
    return price_frame(seed=1, base=100.0)


@pytest.fixture(scope="module")
def bench_hist():
    return price_frame(seed=2, base=300.0)


def test_returns_calendar_anchored(ticker_hist, bench_hist):
    assert md.compute_returns(ticker_hist) == {"r1d": 0.46, "r5d": 1.85, "r20d": 0.43}
    assert md.compute_returns(bench_hist) == {"r1d": 0.21, "r5d": 0.85, "r20d": 0.2}


def test_relative_strength_values(ticker_hist, bench_hist):
    # P3 declared edit: relative_strength gained the Mansfield regime fields.
    assert md.relative_strength(ticker_hist, bench_hist) == {
        "rs5d": 1.0, "rs20d": 0.23,
        "rs_trend": "outperforming", "rs_line_ma50_dist_pct": 1.45,
    }


def test_positional_fallback_when_anchor_date_missing(ticker_hist):
    # Drop the session exactly 5 trading days back: the calendar anchor is absent
    # from the index, so compute_returns falls back to positional iloc[-(n+1)].
    gappy = ticker_hist.drop(ticker_hist.index[-6])
    assert md.compute_returns(gappy) == {"r1d": 0.46, "r5d": 2.06, "r20d": 0.43}


def test_empty_frame_yields_all_none():
    import pandas as pd

    assert md.compute_returns(pd.DataFrame()) == {"r1d": None, "r5d": None, "r20d": None}
    assert md.relative_strength(pd.DataFrame(), pd.DataFrame()) == {
        "rs5d": None, "rs20d": None, "rs_trend": None, "rs_line_ma50_dist_pct": None,
    }
