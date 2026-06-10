"""Integration tests for store.get_fundamentals: the QoQ merge must FILL the cache's
null QoQ/margin without ever overwriting the cache's TTM growth, and must degrade to
insufficient when stale. Highest-stakes invariant for trading decisions."""
from datetime import date, datetime, timedelta, timezone

from tracker import store
from tracker.quarterly import Quarter

NOW = datetime.now(timezone.utc)


def _patch(monkeypatch, cache, row, quarters=None, compute=None):
    monkeypatch.setattr(store.cache_source, "get_fundamentals", lambda t: cache)
    monkeypatch.setattr(store.db, "using_db", lambda: True)
    monkeypatch.setattr(store.db, "fetch_fundamentals", lambda t: row)
    monkeypatch.setattr(store.db, "upsert_fundamentals", lambda t, d: None)
    if quarters is not None:
        monkeypatch.setattr(store.quarterly, "fetch_quarters", lambda t: quarters)
    if compute is not None:
        monkeypatch.setattr(store.fundamentals, "compute", lambda t: compute)


def test_covered_fresh_fills_qoq_keeps_ttm(monkeypatch):
    cache = {"revenue_yoy": 30.0, "eps_yoy": 20.0, "gross_margin": 50.0,
             "revenue_qoq_pct": None, "gross_margin_qoq_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 4, 30),
           "fetched_at": NOW - timedelta(days=1), "revenue_qoq_pct": 12.0, "gross_margin_qoq_pp": 0.9}
    _patch(monkeypatch, cache, row)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-05-14"})  # ~14d gap: current
    assert f["revenue_qoq_pct"] == 12.0 and f["gross_margin_qoq_pp"] == 0.9  # filled
    assert f["revenue_yoy"] == 30.0 and f["eps_yoy"] == 20.0  # TTM preserved
    assert f.get("fundamentals_stale") is not True


def test_covered_stale_nulls_qoq_keeps_ttm(monkeypatch):
    cache = {"revenue_yoy": 30.0, "eps_yoy": 20.0, "revenue_qoq_pct": None, "gross_margin_qoq_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 1, 31), "fetched_at": NOW - timedelta(days=1)}
    # yfinance still only has the Jan quarter (lag) -> not advanced -> stale
    quarters = [Quarter(date(2026, 1, 31), revenue=100.0, gross_profit=50.0),
                Quarter(date(2025, 10, 31), revenue=95.0, gross_profit=47.0)]
    _patch(monkeypatch, cache, row, quarters=quarters)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-06-03"})  # ~123d gap: behind
    assert f["revenue_qoq_pct"] is None and f["gross_margin_qoq_pp"] is None  # degraded
    assert f.get("fundamentals_stale") is True
    assert f["revenue_yoy"] == 30.0 and f["eps_yoy"] == 20.0  # TTM still preserved


def test_covered_does_not_overwrite_present_qoq(monkeypatch):
    # if the cache somehow already had a QoQ, the fill-null must not clobber it
    cache = {"revenue_yoy": 30.0, "revenue_qoq_pct": 7.7, "gross_margin_qoq_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 4, 30),
           "fetched_at": NOW - timedelta(days=1), "revenue_qoq_pct": 12.0, "gross_margin_qoq_pp": 0.9}
    _patch(monkeypatch, cache, row)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-05-14"})
    assert f["revenue_qoq_pct"] == 7.7  # not overwritten
    assert f["gross_margin_qoq_pp"] == 0.9  # filled (was null)


def test_covered_fresh_fills_margin_yoy_pp(monkeypatch):
    """P4 wiring proof: the cache can't supply margin YoY; the quarterly overlay
    must fill it at the STORE level (not just exist in quarterly.py)."""
    cache = {"revenue_yoy": 30.0, "revenue_qoq_pct": None, "gross_margin_qoq_pp": None,
             "gross_margin_yoy_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 4, 30),
           "fetched_at": NOW - timedelta(days=1), "revenue_qoq_pct": 12.0,
           "gross_margin_qoq_pp": -2.5, "gross_margin_yoy_pp": -1.5}
    _patch(monkeypatch, cache, row)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-05-14"})
    assert f["gross_margin_yoy_pp"] == -1.5
    assert f["revenue_yoy"] == 30.0  # TTM untouched


def test_covered_stale_nulls_margin_yoy_pp(monkeypatch):
    cache = {"revenue_yoy": 30.0, "revenue_qoq_pct": None, "gross_margin_qoq_pp": None,
             "gross_margin_yoy_pp": None}
    row = {"ticker": "X", "report_date": date(2026, 1, 31),
           "fetched_at": NOW - timedelta(days=1), "gross_margin_yoy_pp": -1.5}
    quarters = [Quarter(date(2026, 1, 31), revenue=100.0, gross_profit=50.0),
                Quarter(date(2025, 10, 31), revenue=95.0, gross_profit=47.0)]
    _patch(monkeypatch, cache, row, quarters=quarters)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-06-03"})  # behind
    assert f["gross_margin_yoy_pp"] is None  # degraded with the QoQ fields
    assert f.get("fundamentals_stale") is True


def test_uncovered_behind_degrades_qoq(monkeypatch):
    compute = {"report_date": "2026-01-31", "revenue_qoq_pct": 5.0, "gross_margin_qoq_pp": 1.0,
               "revenue_yoy": 30.0, "eps_yoy": 20.0}
    _patch(monkeypatch, cache=None, row=None, compute=compute)
    f = store.get_fundamentals("X", earnings={"last_date": "2026-06-03"})  # behind
    assert f["revenue_qoq_pct"] is None and f["gross_margin_qoq_pp"] is None
    assert f.get("fundamentals_stale") is True
    assert f["revenue_yoy"] == 30.0  # TTM-equivalent own-fetch growth preserved
