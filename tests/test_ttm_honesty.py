"""P7 gate: TTM honesty (D1).

~18/22 names get TTM growth from the equity-research cache but displayed it under
a "YoY" label, and the rules ran on it (TTM lags a real rollover by ~2 quarters).
Now: (1) the label says TTM when the value IS TTM; (2) the rules prefer our own
single-quarter YoY (revenue_yoy_q / eps_yoy_q, guarded) when the quarterly table
has it; (3) a fresh post-earnings window hard-gates stale cache TTM to None.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from tracker import signals, store

ET = ZoneInfo("America/New_York")
CFG = {"signals": {"rsi_overbought": 70, "rsi_oversold": 30,
                   "extended_above_sma20_pct": 12.0, "earnings_soon_days": 7}}


def _row(fund):
    return {"technicals": {"trend": "mixed", "ma_cross": "above", "rsi14": 50.0},
            "position": {"held": True, "shares": 10.0}, "earnings": {"days_until_next": 30},
            "fundamentals": fund, "thesis_break": {},
            "relative_strength": {"rs20d": 1.0, "rs_trend": "outperforming"}}


def _rev_badge(fund):
    out = signals.build_signals(_row(fund), CFG)
    return next((b["label"] for b in out["badges"] if b["label"].startswith("Rev ")), None)


# ── labels ────────────────────────────────────────────────────────────────

def test_cache_ttm_value_is_labelled_ttm():
    assert _rev_badge({"source": "equity-cache(fmp,ttm)", "revenue_yoy": 25.0}) == "Rev +25% TTM"


def test_quarterly_yoy_preferred_and_labelled_yoy():
    fund = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 25.0, "revenue_yoy_q": -5.0}
    assert _rev_badge(fund) == "Rev -5% YoY"


def test_own_fetch_yoy_stays_yoy():
    assert _rev_badge({"source": "fmp", "revenue_yoy": 20.0}) == "Rev +20% YoY"


# ── rule preference (all four combos + the conflict case) ────────────────

def _det(fund):
    return signals.provisional_lean(_row(fund), CFG)["drivers"]["deterioration"]


def test_conflict_q_yoy_negative_beats_ttm_positive():
    # THE point of D1: TTM still shows +20 while the latest quarter is -5 —
    # deterioration must be caught a quarter earlier.
    fund = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 20.0, "revenue_yoy_q": -5.0}
    assert "revenue_weakening" in _det(fund)


def test_q_yoy_positive_overrides_negative_ttm():
    fund = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": -3.0, "revenue_yoy_q": 8.0}
    assert "revenue_weakening" not in _det(fund)


def test_falls_back_to_ttm_when_no_quarterly():
    assert "revenue_weakening" in _det({"source": "equity-cache(fmp,ttm)", "revenue_yoy": -3.0})
    assert "revenue_weakening" not in _det({"source": "equity-cache(fmp,ttm)", "revenue_yoy": 12.0})


def test_eps_preference_mirrors_revenue():
    fund = {"source": "equity-cache(fmp,ttm)", "eps_yoy": 15.0, "eps_yoy_q": -10.0}
    assert "earnings_quality_deteriorating" in _det(fund)


# ── store overlay: *_q coexists with TTM, degrades when stale ─────────────

NOW = datetime.now(timezone.utc)


def _patch(monkeypatch, cache, row):
    monkeypatch.setattr(store.cache_source, "get_fundamentals", lambda t: cache)
    monkeypatch.setattr(store.cache_source, "get_fmp_refreshed_at", lambda: NOW)
    monkeypatch.setattr(store.db, "using_db", lambda: True)
    monkeypatch.setattr(store.db, "fetch_fundamentals", lambda t: row)
    monkeypatch.setattr(store.db, "upsert_fundamentals", lambda t, d: None)


def test_overlay_adds_q_yoy_without_touching_ttm(monkeypatch):
    cache = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 30.0, "eps_yoy": 20.0,
             "revenue_qoq_pct": None, "gross_margin_qoq_pp": None, "gross_margin_yoy_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 4, 30), "fetched_at": NOW - timedelta(days=1),
           "revenue_yoy": 12.0, "eps_yoy": -4.0, "revenue_qoq_pct": 3.0}
    _patch(monkeypatch, cache, row)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-05-14"})
    assert f["revenue_yoy"] == 30.0 and f["eps_yoy"] == 20.0       # TTM intact
    assert f["revenue_yoy_q"] == 12.0 and f["eps_yoy_q"] == -4.0   # quarter added


def test_overlay_q_yoy_nulled_when_quarter_stale(monkeypatch):
    from tracker.quarterly import Quarter

    cache = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 30.0,
             "revenue_qoq_pct": None, "gross_margin_qoq_pp": None, "gross_margin_yoy_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 1, 31), "fetched_at": NOW - timedelta(days=1),
           "revenue_yoy": 12.0}
    monkeypatch.setattr(store.quarterly, "fetch_quarters",
                        lambda t: [Quarter(date(2026, 1, 31), revenue=100.0, gross_profit=50.0)])
    _patch(monkeypatch, cache, row)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-06-03"})  # behind
    assert f.get("revenue_yoy_q") is None
    assert f["revenue_yoy"] == 30.0  # TTM never nulled by QUARTER staleness


# ── post-earnings TTM gate (pure semantics, pinned AMC-safe) ──────────────

def _et(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=ET)


def test_gate_pure_function_semantics():
    s = store._ttm_stale
    # reported yesterday, cache refreshed BEFORE the report day ended -> stale
    assert s(date(2026, 6, 8), _et(2026, 6, 8, 9), _et(2026, 6, 9, 17)) is True
    # AMC edge: refreshed the same evening (17:30) still counts stale (cutoff is
    # next midnight ET — conservative, at most one extra day of 'updating')
    assert s(date(2026, 6, 8), _et(2026, 6, 8, 17, ), _et(2026, 6, 9, 9)) is True
    # refreshed after the report day ended -> fresh
    assert s(date(2026, 6, 8), _et(2026, 6, 9, 17), _et(2026, 6, 10, 9)) is False
    # old earnings (outside the 2-day window) -> no gate at all
    assert s(date(2026, 5, 1), _et(2026, 5, 2, 1), _et(2026, 6, 9, 9)) is False
    # no refresh timestamp at all inside the window -> stale (conservative)
    assert s(date(2026, 6, 8), None, _et(2026, 6, 9, 9)) is True
    # no last_date -> never stale
    assert s(None, _et(2026, 6, 9), _et(2026, 6, 9, 9)) is False


def test_gate_nulls_ttm_growth_in_cached_path(monkeypatch):
    cache = {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 30.0, "eps_yoy": 20.0,
             "gross_margin": 50.0, "revenue_qoq_pct": None, "gross_margin_qoq_pp": None,
             "gross_margin_yoy_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 6, 8), "fetched_at": NOW}
    _patch(monkeypatch, cache, row)
    # reported yesterday; cache batch is older than the report day's end
    monkeypatch.setattr(store.cache_source, "get_fmp_refreshed_at",
                        lambda: _et(2026, 6, 8, 9))
    monkeypatch.setattr(store, "_now_et", lambda: _et(2026, 6, 9, 9))
    f = store.get_fundamentals("X", earnings={"last_date": "2026-06-08"})
    assert f["revenue_yoy"] is None and f["eps_yoy"] is None  # gated
    assert f["ttm_stale"] is True
    assert f["gross_margin"] == 50.0  # only GROWTH fields are gated
