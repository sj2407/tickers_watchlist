"""P0 characterization: pins the revenue-growth badge text/tone BEFORE P7 makes
the label source-aware (YoY vs TTM). The P7 phase declares its update to these.
"""
from tracker import signals

CFG = {"signals": {"rsi_overbought": 70, "rsi_oversold": 30, "rel_vol_spike": 2.0,
                   "extended_above_sma20_pct": 12.0, "earnings_soon_days": 7}}


def _row(fund):
    return {"technicals": {}, "position": {}, "earnings": {}, "fundamentals": fund,
            "thesis_break": {}, "relative_strength": {}}


def _rev_badge(fund):
    out = signals.build_signals(_row(fund), CFG)
    return next((b for b in out["badges"] if b["label"].startswith("Rev ")), None)


def test_strong_growth_badge_good():
    assert _rev_badge({"revenue_yoy": 20.0}) == {"label": "Rev +20% YoY", "tone": "good"}


def test_negative_growth_badge_bad():
    assert _rev_badge({"revenue_yoy": -5.0}) == {"label": "Rev -5% YoY", "tone": "bad"}


def test_modest_growth_badge_info():
    assert _rev_badge({"revenue_yoy": 7.0}) == {"label": "Rev +7% YoY", "tone": "info"}


def test_missing_growth_no_badge():
    assert _rev_badge({}) is None
    assert _rev_badge({"revenue_yoy": None}) is None
