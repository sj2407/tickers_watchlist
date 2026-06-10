"""P4b gate: hard/soft trim confluence (provisional, config-tunable — D2).

Hard dimensions: confirmed downtrend, revenue weakening, SEVERE margin collapse.
Soft: underperforming RS regime, mild margin compression, earnings quality.
`trim` needs >=2 dimensions INCLUDING >=1 hard; a soft-only confluence is a
`hold` with a visible review driver + badge — surfaced, never an auto-trim.
Severity comes from thesis_break.margin_severe; the engine NEVER re-derives it.
"""
from tracker import signals

CFG = {"signals": {"rsi_overbought": 70, "rsi_oversold": 30,
                   "extended_above_sma20_pct": 12.0, "earnings_soon_days": 7}}


def mk(trend="mixed", ma_cross="above", rs_trend="outperforming",
       rev_yoy=20.0, eps_yoy=20.0, tb=None):
    return {
        "technicals": {"trend": trend, "ma_cross": ma_cross, "rsi14": 50.0, "dist_sma20_pct": 2.0},
        "position": {"held": True, "shares": 10.0},
        "earnings": {"days_until_next": 30},
        "fundamentals": {"revenue_yoy": rev_yoy, "eps_yoy": eps_yoy},
        "relative_strength": {"rs20d": 1.0, "rs_trend": rs_trend},
        "thesis_break": tb or {},
    }


def test_soft_plus_soft_is_hold_with_review_not_trim():
    """THE regression case: today's HIMS/IONQ/MP/OUST trim proposals were all
    soft+soft (lagging RS + mild margin). Under P4b: hold + review, visible."""
    tb = {"margin_compression": True, "margin_severe": False, "any": True}
    out = signals.provisional_lean(mk(rs_trend="underperforming", tb=tb), CFG)
    assert out["lean"] == "hold"
    assert out["drivers"]["review"]                      # surfaced, not silent
    assert set(out["drivers"]["deterioration"]) == {"negative_rel_strength", "margin_compression"}


def test_hard_plus_soft_is_trim():
    out = signals.provisional_lean(
        mk(trend="downtrend", ma_cross="below", rs_trend="underperforming"), CFG)
    assert out["lean"] == "trim"


def test_hard_plus_hard_is_trim():
    out = signals.provisional_lean(
        mk(trend="downtrend", ma_cross="below", rev_yoy=-5.0), CFG)
    assert out["lean"] == "trim"


def test_one_hard_alone_is_still_hold():
    out = signals.provisional_lean(mk(trend="downtrend", ma_cross="below"), CFG)
    assert out["lean"] == "hold"
    assert not out["drivers"].get("review")  # one signal isn't a confluence


def test_severe_margin_is_hard_and_comes_from_thesis_not_rederived():
    # margin_severe=True with NO margin numbers present: the engine must trust
    # the thesis output, not recompute the threshold from raw fields.
    tb = {"margin_compression": True, "margin_severe": True, "any": True}
    out = signals.provisional_lean(mk(rs_trend="underperforming", tb=tb), CFG)
    assert out["lean"] == "trim"


def test_mild_margin_is_soft():
    tb = {"margin_compression": True, "margin_severe": False, "any": True}
    out = signals.provisional_lean(
        mk(rs_trend="underperforming", tb=tb), CFG)
    assert out["lean"] == "hold"  # soft+soft


def test_review_badge_emitted_for_soft_confluence():
    tb = {"margin_compression": True, "margin_severe": False, "any": True}
    row = mk(rs_trend="underperforming", tb=tb)
    out = signals.build_signals(row, CFG)
    assert any(b["label"] == "Review" for b in out["badges"])
    assert out["provisional_lean"] == "hold"


def test_no_review_badge_when_clean():
    out = signals.build_signals(mk(), CFG)
    assert not any(b["label"] == "Review" for b in out["badges"])


def test_hard_dimensions_config_tunable():
    cfg = {"signals": {**CFG["signals"],
                       "hard_dimensions": ["negative_rel_strength", "downtrend",
                                           "revenue_weakening", "margin_severe"]}}
    tb = {"margin_compression": True, "margin_severe": False, "any": True}
    out = signals.provisional_lean(mk(rs_trend="underperforming", tb=tb), cfg)
    assert out["lean"] == "trim"  # RS reclassified hard by config -> trims again
