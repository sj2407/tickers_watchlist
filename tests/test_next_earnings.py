"""P0 characterization: pins snapshot._next_earnings BEFORE P5 rewrites date
selection. Today's (pre-P5) contract: Finnhub calendar and yfinance dates are
UNIONED; the earliest upcoming date wins; last-quarter actuals + surprise come
from the Finnhub row matching the most recent past date.
"""
from datetime import date

import pytest

from tracker import snapshot, sources, db


TODAY = date(2026, 6, 9)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # File mode: api_cache becomes a passthrough (no DB, nothing stored).
    monkeypatch.setattr(db, "using_db", lambda: False)


def _cal(rows):
    return lambda ticker: rows


def test_upcoming_and_last_from_finnhub_calendar(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", _cal([
        {"date": "2026-06-16", "hour": "amc", "eps_estimate": 1.5,
         "eps_actual": None, "revenue_estimate": 2.0e9, "revenue_actual": None},
        {"date": "2026-03-10", "hour": "amc", "eps_estimate": 1.0,
         "eps_actual": 1.2, "revenue_estimate": 1.8e9, "revenue_actual": 1.9e9},
    ]))
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda t: [])
    out = snapshot._next_earnings("X", TODAY)
    assert out["next_date"] == "2026-06-16" and out["days_until_next"] == 7
    assert out["next_hour"] == "amc" and out["next_eps_estimate"] == 1.5
    assert out["last_date"] == "2026-03-10"
    assert out["last_eps_actual"] == 1.2
    assert out["last_eps_surprise_pct"] == 20.0  # (1.2-1.0)/1.0


def test_finnhub_confirmed_date_wins_over_yf_estimate(monkeypatch):
    # P5 declared update: pre-P5 the earliest UNION date won (yf phantom 6/12 beat
    # Finnhub's confirmed 6/16). Now the confirmed calendar is authoritative.
    monkeypatch.setattr(sources, "earnings_calendar", _cal([
        {"date": "2026-06-16", "hour": "amc", "eps_estimate": 1.5,
         "eps_actual": None, "revenue_estimate": None, "revenue_actual": None},
    ]))
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda t: [date(2026, 6, 12)])
    out = snapshot._next_earnings("X", TODAY)
    assert out["next_date"] == "2026-06-16" and out["days_until_next"] == 7
    assert out["next_hour"] == "amc"


def test_no_data_at_all_is_empty_dict(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", _cal([]))
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda t: [])
    assert snapshot._next_earnings("X", TODAY) == {}


def test_zero_estimate_never_divides(monkeypatch):
    monkeypatch.setattr(sources, "earnings_calendar", _cal([
        {"date": "2026-03-10", "hour": "amc", "eps_estimate": 0,
         "eps_actual": 0.5, "revenue_estimate": None, "revenue_actual": None},
    ]))
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda t: [])
    out = snapshot._next_earnings("X", TODAY)
    assert "last_eps_surprise_pct" not in out
