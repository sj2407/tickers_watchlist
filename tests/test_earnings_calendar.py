"""P5 gate: a failed earnings-calendar fetch is never cached as "no earnings";
confirmed (Finnhub) dates beat yfinance estimates; alerts are in-window with the
big_move mode gate.

Cache tests are anchored at the REAL storage seam (api_cache._get/_put faked with
a recording dict) — a file-mode passthrough test would pass before the fix and
prove nothing.
"""
from datetime import date

import pytest

from tracker import api_cache, db, snapshot, sources

TODAY = date(2026, 6, 9)


# ── sources contract: None = failure, [] = confirmed empty ────────────────

def test_transport_failure_returns_none(monkeypatch):
    monkeypatch.setattr(sources, "_finnhub_get", lambda path, params: None)
    assert sources.earnings_calendar("X") is None


def test_confirmed_empty_returns_empty_list(monkeypatch):
    monkeypatch.setattr(sources, "_finnhub_get", lambda path, params: {"earningsCalendar": []})
    assert sources.earnings_calendar("X") == []


# ── cache seam: failure never cached; confirmed-empty cached once ─────────

@pytest.fixture()
def fake_store(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(api_cache, "_get", lambda key, now=None: store.get(key))
    monkeypatch.setattr(api_cache, "_put", lambda key, val, now=None: store.__setitem__(key, val))
    return store


def test_failure_is_not_cached_and_retries(fake_store):
    calls = {"n": 0}

    def failing_fetch():
        calls["n"] += 1
        return None  # transport failure

    assert api_cache.cached("k", failing_fetch) is None
    assert fake_store == {}                      # nothing poisoned
    api_cache.cached("k", failing_fetch)
    assert calls["n"] == 2                       # second call re-fetched


def test_confirmed_empty_is_cached_once(fake_store):
    calls = {"n": 0}

    def empty_fetch():
        calls["n"] += 1
        return []  # Finnhub answered: genuinely nothing in the window

    assert api_cache.cached("k", empty_fetch) == []
    assert api_cache.cached("k", empty_fetch) == []
    assert calls["n"] == 1                       # served from cache


def test_recovery_after_failure_caches_real_data(fake_store):
    responses = iter([None, [{"date": "2026-06-16"}]])
    fetch = lambda: next(responses)
    assert api_cache.cached("k", fetch) is None          # failure → uncached
    assert api_cache.cached("k", fetch) == [{"date": "2026-06-16"}]
    assert fake_store["k"] == [{"date": "2026-06-16"}]   # recovery cached


# ── date selection: Finnhub-confirmed first ───────────────────────────────

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(db, "using_db", lambda: False)  # api_cache passthrough


def test_finnhub_confirmed_beats_earlier_yf_estimate(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", lambda tk: [
        {"date": "2026-06-16", "hour": "amc", "eps_estimate": 1.5,
         "eps_actual": None, "revenue_estimate": None, "revenue_actual": None}])
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda tk: [date(2026, 6, 12)])
    out = snapshot._next_earnings("X", TODAY)
    assert out["next_date"] == "2026-06-16"      # phantom 6/12 ignored
    assert "next_date_estimated" not in out


def test_yf_fallback_when_finnhub_confirmed_empty_is_unflagged(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", lambda tk: [])
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda tk: [date(2026, 7, 1)])
    out = snapshot._next_earnings("X", TODAY)
    assert out["next_date"] == "2026-07-01"
    assert "next_date_estimated" not in out


def test_yf_fallback_when_finnhub_failed_is_flagged_estimated(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", lambda tk: None)
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda tk: [date(2026, 7, 1)])
    out = snapshot._next_earnings("X", TODAY)
    assert out["next_date"] == "2026-07-01"
    assert out["next_date_estimated"] is True


def test_past_dates_still_union_for_actuals(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", lambda tk: [
        {"date": "2026-03-10", "hour": "amc", "eps_estimate": 1.0, "eps_actual": 1.2,
         "revenue_estimate": None, "revenue_actual": None}])
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda tk: [date(2026, 4, 2)])
    out = snapshot._next_earnings("X", TODAY)
    assert out["last_date"] == "2026-04-02"      # union picks the latest past date


# ── alerts: in-window + mode gate ─────────────────────────────────────────

def _row(days=None, chg=None, estimated=False):
    earn = {"days_until_next": days, "next_date": "2026-06-16", "next_hour": "amc"}
    if estimated:
        earn["next_date_estimated"] = True
    return {"ticker": "AAA", "earnings": earn, "price": {"day_change_pct": chg}}


def _types(rows, mode):
    return [a["type"] for a in snapshot._mechanical_alerts(rows, {}, mode)]


def test_t7_fires_across_the_window_not_exact_day():
    assert "earnings_t7" in _types([_row(days=7)], "postclose")
    assert "earnings_t7" in _types([_row(days=6)], "postclose")  # the missed-run case
    assert "earnings_t7" in _types([_row(days=3)], "postclose")
    assert "earnings_t7" not in _types([_row(days=8)], "postclose")
    assert "earnings_t7" not in _types([_row(days=1)], "postclose")  # t1 territory


def test_t1_fires_at_one_and_zero_days_only():
    assert "earnings_t1" in _types([_row(days=1)], "postclose")
    assert "earnings_t1" in _types([_row(days=0)], "postclose")
    assert "earnings_t1" not in _types([_row(days=2)], "postclose")


def test_estimated_date_is_labelled_unconfirmed():
    alerts = snapshot._mechanical_alerts([_row(days=5, estimated=True)], {}, "postclose")
    assert "(date unconfirmed)" in alerts[0]["msg"]


def test_big_move_suppressed_at_preopen_only():
    assert "big_move" not in _types([_row(chg=8.0)], "preopen")   # yesterday's move
    assert "big_move" in _types([_row(chg=8.0)], "intraday")
    assert "big_move" in _types([_row(chg=-8.0)], "postclose")
