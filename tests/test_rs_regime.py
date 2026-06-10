"""P3 gate: relative-strength deterioration = the Mansfield/Weinstein REGIME test
(RS line below its own 50-session MA), replacing the old any-magnitude rs20d<0.

The HIMS case (live, 2026-06-10): rs20d −0.77pp counted as a full deterioration
dimension and made half a trim confluence. Under the regime test a name must be
PERSISTENTLY lagging — a slightly-behind fortnight inside an outperforming regime
must not flag.
"""
import numpy as np
import pandas as pd
import pytest

from tests.synth import sessions
from tracker import market_data as md
from tracker import signals

CFG = {"signals": {"rsi_overbought": 70, "rsi_oversold": 30,
                   "extended_above_sma20_pct": 12.0, "earnings_soon_days": 7}}


def _frame(closes):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions()[-len(closes):]])
    c = np.asarray(closes, dtype=float)
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c,
                         "Volume": np.full(len(c), 1e6)}, index=idx)


def test_steady_laggard_is_underperforming():
    n = 120
    bench = _frame(100 + np.arange(n) * 0.5)          # market rising
    tick = _frame(np.full(n, 100.0))                   # name flat -> ratio falling
    rs = md.relative_strength(tick, bench)
    assert rs["rs_trend"] == "underperforming"
    assert rs["rs_line_ma50_dist_pct"] < 0


def test_hims_case_brief_lag_inside_strong_regime_not_flagged():
    # 100 sessions of clear outperformance, then ~10 sessions slightly behind:
    # the RS line dips but stays above its 50-session MA -> still outperforming.
    n = 120
    bench = _frame(np.full(n, 100.0))
    tick_closes = np.concatenate([100 * (1.004 ** np.arange(n - 10)),     # +0.4%/day vs flat bench
                                  100 * (1.004 ** (n - 11)) * (0.999 ** np.arange(1, 11))])
    tick = _frame(tick_closes)
    rs = md.relative_strength(tick, bench)
    assert rs["rs_trend"] == "outperforming"
    assert rs["rs_line_ma50_dist_pct"] > 0


def test_constant_ratio_boundary_is_outperforming():
    n = 120
    bench = _frame(100 + np.arange(n) * 0.5)
    rs = md.relative_strength(bench.copy(), bench)     # ratio exactly 1 forever
    assert rs["rs_line_ma50_dist_pct"] == 0.0
    assert rs["rs_trend"] == "outperforming"           # >= 0 is not deterioration


def test_insufficient_history_is_null_never_flags():
    n = 40                                             # < 50-session MA window
    bench = _frame(100 + np.arange(n) * 0.5)
    tick = _frame(np.full(n, 100.0))
    rs = md.relative_strength(tick, bench)
    assert rs["rs_trend"] is None
    assert rs["rs_line_ma50_dist_pct"] is None
    # and a null regime can never count as deterioration
    row = {"technicals": {"trend": "downtrend", "ma_cross": "below"},
           "position": {"held": True, "shares": 1.0}, "earnings": {},
           "fundamentals": {}, "relative_strength": rs, "thesis_break": {}}
    out = signals.provisional_lean(row, CFG)
    assert "negative_rel_strength" not in out["drivers"]["deterioration"]


# ── engine wiring ───────────────────────────────────────────────────────

def _row(rs20=1.0, rs_trend="outperforming", trend="mixed", ma_cross="above", tb=None):
    return {
        "technicals": {"trend": trend, "ma_cross": ma_cross, "rsi14": 50.0, "dist_sma20_pct": 2.0},
        "position": {"held": True, "shares": 10.0},
        "earnings": {"days_until_next": 30},
        "fundamentals": {"revenue_yoy": 20.0, "eps_yoy": 20.0},
        "relative_strength": {"rs20d": rs20, "rs_trend": rs_trend},
        "thesis_break": tb or {},
    }


def test_small_negative_rs20d_in_good_regime_plus_flag_is_hold():
    # THE old bug: -0.77pp + one thesis flag used to manufacture a trim.
    tb = {"margin_compression": True, "any": True}
    out = signals.provisional_lean(_row(rs20=-0.77, rs_trend="outperforming", tb=tb), CFG)
    assert out["lean"] == "hold"
    assert out["drivers"]["deterioration"] == ["margin_compression"]


def test_underperforming_regime_plus_flag_is_trim():
    # P4b declared edit: a trim needs >=1 HARD dimension, so the margin flag here
    # is severe; the soft+soft original lives on as hold+review in test_confluence.
    tb = {"margin_compression": True, "margin_severe": True, "any": True}
    out = signals.provisional_lean(_row(rs20=-0.77, rs_trend="underperforming", tb=tb), CFG)
    assert out["lean"] == "trim"
    assert "negative_rel_strength" in out["drivers"]["deterioration"]


def test_underperforming_alone_is_hold():
    assert signals.provisional_lean(_row(rs_trend="underperforming"), CFG)["lean"] == "hold"


def test_small_negative_rs20d_blocks_pile_on_but_does_not_trim():
    # pile side pinned: rs_ok still requires rs20d >= 0, regardless of regime.
    out = signals.provisional_lean(_row(rs20=-1.0, rs_trend="outperforming", trend="uptrend"), CFG)
    assert out["lean"] == "hold"


def test_regime_flips_when_the_rs_line_crosses_its_ma():
    """Review R2-3: one series that CROSSES — outperforming early, then a hard
    fade pulls the RS line below its own 50-session MA and the regime flips."""
    n = 130
    bench = _frame(np.full(n, 100.0))
    up = 100 * (1.004 ** np.arange(100))                      # 100 strong sessions
    down = up[-1] * (0.99 ** np.arange(1, 31))                # 30-session fade
    tick = _frame(np.concatenate([up, down]))
    assert md.relative_strength(tick, bench)["rs_trend"] == "underperforming"
    # same series, truncated before the fade: still outperforming
    tick_early = _frame(up)
    bench_early = _frame(np.full(100, 100.0))
    assert md.relative_strength(tick_early, bench_early)["rs_trend"] == "outperforming"
