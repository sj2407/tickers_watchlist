"""Cache-source: freshness gating + metric mapping, against a synthetic temp DB
(no dependency on the real equity-research cache)."""
import sqlite3
from datetime import datetime, timezone, timedelta

import pytest

from tracker import cache_source as cs


def _build_db(path, fmp_age_hours=2):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    c.execute("CREATE TABLE fundamentals (ticker TEXT, metric TEXT, value REAL, period_end TEXT, source TEXT, fetched_at TEXT)")
    fresh = (datetime.now(timezone.utc) - timedelta(hours=fmp_age_hours)).isoformat()
    c.execute("INSERT INTO meta VALUES ('fmp_refreshed_at', ?)", (fresh,))
    rows = [("NVDA", "pe_ratio", 33.0), ("NVDA", "gross_margin", 0.74),
            ("NVDA", "revenue_growth_ttm", 0.65), ("NVDA", "eps_growth_ttm", 0.66)]
    for tk, m, v in rows:
        c.execute("INSERT INTO fundamentals VALUES (?,?,?,?,?,?)", (tk, m, v, None, "fmp", fresh))
    c.commit(); c.close()


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    db = tmp_path / "cache.db"
    monkeypatch.setattr(cs, "CACHE_DB", str(db))
    monkeypatch.setenv("WATCHLIST_USE_CACHE", "1")
    return db


def test_maps_and_scales_metrics(temp_cache):
    _build_db(temp_cache)
    f = cs.get_fundamentals("NVDA")
    assert f["source"].startswith("equity-cache")
    assert f["pe"] == 33.0
    assert f["gross_margin"] == 74.0          # 0.74 → 74%
    assert f["revenue_yoy"] == 65.0           # 0.65 → 65%


def test_stale_returns_none(temp_cache):
    _build_db(temp_cache, fmp_age_hours=100)  # older than 36h tolerance
    assert cs.get_fundamentals("NVDA") is None


def test_uncovered_ticker_returns_none(temp_cache):
    _build_db(temp_cache)
    assert cs.get_fundamentals("ZZZZ") is None


def test_disabled_via_env(temp_cache, monkeypatch):
    _build_db(temp_cache)
    monkeypatch.setenv("WATCHLIST_USE_CACHE", "0")
    assert cs.available() is False
    assert cs.get_fundamentals("NVDA") is None


def test_absent_cache_is_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "CACHE_DB", str(tmp_path / "nope.db"))
    assert cs.available() is False
    assert cs.get_fundamentals("NVDA") is None
