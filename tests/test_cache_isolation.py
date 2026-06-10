"""P0 hard-constraint guard: the equity-research-agent cache is NEVER touched.

Runtime proof, not a grep: build a real temp SQLite cache, hash the file, run every
public cache_source getter, then assert (a) the file bytes are unchanged and (b) every
sqlite3.connect call used a read-only URI. Plus a repo-scope check that no other
module references the cache path env vars.
"""
import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tracker import cache_source


@pytest.fixture()
def temp_cache(tmp_path, monkeypatch):
    db_path = tmp_path / "cache.db"
    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE fundamentals (ticker TEXT, metric TEXT, value REAL, fetched_at TEXT);
        CREATE TABLE earnings_actuals (
          ticker TEXT, report_date TEXT, eps_actual REAL, eps_estimate REAL,
          eps_surprise_pct REAL, revenue_surprise_pct REAL,
          price_reaction_1d REAL, price_reaction_5d REAL);
        CREATE TABLE scores (
          ticker TEXT, value_z REAL, quality_z REAL, growth_z REAL, health_z REAL,
          momentum_z REAL, composite REAL, rank INTEGER, as_of TEXT);
        """
    )
    conn.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("fmp_refreshed_at", now), ("actuals_refreshed_at", now), ("scores_computed_at", now),
    ])
    conn.executemany("INSERT INTO fundamentals VALUES (?, ?, ?, ?)", [
        ("AAA", "revenue_growth_ttm", 0.30, now),
        ("AAA", "gross_margin", 0.55, now),
        ("AAA", "pe_ratio", 28.0, now),
    ])
    conn.execute("INSERT INTO earnings_actuals VALUES ('AAA','2026-05-10',1.2,1.0,20.0,3.0,5.0,7.0)")
    conn.execute("INSERT INTO scores VALUES ('AAA',0.1,0.2,0.3,0.4,0.5,0.6,12,'2026-06-08')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(cache_source, "CACHE_DB", str(db_path))
    monkeypatch.setenv("WATCHLIST_USE_CACHE", "1")
    return db_path


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _public_getters():
    """Every public callable in cache_source taking a ticker-or-nothing — including
    accessors added later (e.g. P7's get_fmp_refreshed_at) without editing this test."""
    out = []
    for name in dir(cache_source):
        if name.startswith(("get_",)) and callable(getattr(cache_source, name)):
            out.append(getattr(cache_source, name))
    assert out, "no public getters found — did cache_source get renamed?"
    return out


def test_cache_file_never_modified_and_opened_read_only(temp_cache, monkeypatch):
    before = _sha(temp_cache)
    uris: list[str] = []
    real_connect = sqlite3.connect

    def recording_connect(target, *a, **kw):
        uris.append(str(target))
        return real_connect(target, *a, **kw)

    monkeypatch.setattr(sqlite3, "connect", recording_connect)

    for fn in _public_getters():
        try:
            fn("AAA")
        except TypeError:
            fn()  # zero-arg accessor (e.g. a meta-timestamp getter)

    assert uris, "no sqlite connection was made — fixture not wired?"
    for uri in uris:
        assert "mode=ro" in uri, f"cache opened writable: {uri}"
    assert _sha(temp_cache) == before, "equity-research cache file was modified!"


def test_getters_actually_returned_data(temp_cache):
    # Guards the guard: an always-failing connector would pass the test above.
    f = cache_source.get_fundamentals("AAA")
    assert f and f["revenue_yoy"] == 30.0 and f["pe"] == 28.0
    assert cache_source.get_earnings_reaction("AAA")["eps_surprise_pct"] == 20.0
    assert cache_source.get_scores("AAA")["rank"] == 12


def test_cache_path_referenced_only_in_cache_source():
    tracker_dir = Path(cache_source.__file__).parent
    pattern = re.compile(r"EQUITY_CACHE_DB|CACHE_DB")
    offenders = []
    for py in tracker_dir.glob("*.py"):
        if py.name == "cache_source.py":
            continue
        if pattern.search(py.read_text()):
            offenders.append(py.name)
    assert not offenders, f"cache path referenced outside cache_source.py: {offenders}"
