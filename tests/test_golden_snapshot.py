"""P0 golden-snapshot diff harness — the cross-phase surgical-ness gate.

Builds a FULL snapshot (postclose + intraday) from a fully deterministic fake world
(no network, no DB, fixed clock) and diffs it against checked-in goldens. Every later
phase may change ONLY the keys it declares; any other drift fails here.

Regenerate after an intentional change:  REGEN_GOLDEN=1 pytest tests/test_golden_snapshot.py
then REVIEW the JSON diff in the commit — regeneration is a declared act, never automatic.
"""
import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tests.synth import price_frame, FIXED_END
from tracker import snapshot, sources, store, db, price_targets

FIXTURES = Path(__file__).parent / "fixtures"
ET = ZoneInfo("America/New_York")
FIXED_NOW = datetime(2026, 6, 9, 17, 0, 0, tzinfo=ET)  # after the close, FIXED_END


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW.astimezone(tz) if tz else FIXED_NOW.replace(tzinfo=None)


TICKERS = ["AAA", "BBB"]
FRAMES = {"AAA": price_frame(1, 100.0), "BBB": price_frame(2, 300.0)}
QUOTES = {
    # AAA: a modest down day (exercises the intraday entry-trigger path);
    # BBB: a big up day (exercises the big_move alert path).
    "AAA": {"last_price": 176.0, "prev_close": 177.48, "open": 177.0,
            "day_high": 178.0, "day_low": 175.5},
    "BBB": {"last_price": 410.0, "prev_close": 380.48, "open": 381.0,
            "day_high": 411.0, "day_low": 380.0},
}
FUNDAMENTALS = {
    "AAA": {"source": "equity-cache(fmp,ttm)", "revenue_yoy": 25.0, "eps_yoy": 18.0,
            "gross_margin": 55.0, "pe": 30.0, "eps_ttm": 5.9,
            "revenue_qoq_pct": 4.0, "gross_margin_qoq_pp": 0.3, "eps_miss_count_last3": 0},
    "BBB": {"source": "fmp", "revenue_yoy": -2.0, "eps_yoy": -10.0,
            "gross_margin": 40.0, "pe": 22.0, "eps_ttm": 18.6,
            "revenue_qoq_pct": -6.0, "gross_margin_qoq_pp": -2.5, "eps_miss_count_last3": 2},
}
EXTRAS = {
    "AAA": {"earnings_reaction": {"report_date": "2026-05-10", "eps_surprise_pct": 12.0,
                                  "price_reaction_1d": 4.0, "price_reaction_5d": 6.0},
            "scores": {"growth_z": 1.2, "quality_z": 0.4, "momentum_z": 0.9,
                       "value_z": -0.5, "health_z": 0.3, "composite": 0.8, "rank": 40}},
    "BBB": {"earnings_reaction": None, "scores": None},
}
EARN_CAL = {
    "AAA": [{"date": "2026-06-16", "hour": "amc", "eps_estimate": 1.5, "eps_actual": None,
             "revenue_estimate": 2.0e9, "revenue_actual": None},
            {"date": "2026-03-10", "hour": "amc", "eps_estimate": 1.0, "eps_actual": 1.2,
             "revenue_estimate": 1.8e9, "revenue_actual": 1.9e9}],
    "BBB": [{"date": "2026-07-30", "hour": "bmo", "eps_estimate": 4.0, "eps_actual": None,
             "revenue_estimate": 9.0e9, "revenue_actual": None},
            {"date": "2026-04-28", "hour": "bmo", "eps_estimate": 3.5, "eps_actual": 3.4,
             "revenue_estimate": 8.5e9, "revenue_actual": 8.4e9}],
}
NEWS = {
    "AAA": [{"datetime": "2026-06-08T14:00:00+00:00", "headline": "AAA wins contract",
             "source": "wire", "url": "https://x/a", "summary": "s", "category": "company"}],
    "BBB": [{"datetime": "2026-06-09T11:00:00+00:00", "headline": "BBB raises guidance",
             "source": "wire", "url": "https://x/b", "summary": "s", "category": "company"}],
}
TARGETS = {
    "AAA": {"low": 150.0, "median": 200.0, "mean": 198.0, "high": 240.0,
            "num_analysts": 20, "source": "yfinance"},
    "BBB": None,
}
PRIOR = {
    "market_recap": "Prior market recap.",
    "macro_context": "Prior macro.",
    "tickers": [
        {"ticker": "AAA", "takeaway": "Prior AAA takeaway", "sentiment": "bullish",
         "catalyst_summary": "Prior catalyst", "earnings_recap": None,
         "final_lean": "hold", "rationale": "Prior rationale",
         "entry_guidance": "Prior entry", "invalidation": "Prior invalidation"},
        # BBB intentionally absent: cold-start path for one name.
    ],
}


@pytest.fixture()
def fake_world(monkeypatch):
    monkeypatch.setattr(db, "using_db", lambda: False)
    # Hermetic: the REAL equity-research cache must never leak into the golden
    # world (data_health would otherwise read the live file's refresh timestamp —
    # machine- and day-dependent).
    monkeypatch.setenv("WATCHLIST_USE_CACHE", "0")
    monkeypatch.setattr(snapshot, "datetime", FrozenDateTime)
    monkeypatch.setattr(snapshot, "session_phase", lambda tz: "afterhours")

    monkeypatch.setattr(sources, "price_history",
                        lambda tk, days=400: FRAMES[tk] if tk in FRAMES else FRAMES["BBB"])
    monkeypatch.setattr(sources, "fast_quote", lambda tk: dict(QUOTES[tk]))
    monkeypatch.setattr(sources, "earnings_calendar", lambda tk, ahead_days=120: EARN_CAL[tk])
    monkeypatch.setattr(sources, "earnings_dates_yf", lambda tk: [])
    monkeypatch.setattr(sources, "company_news", lambda tk, lb, lim: NEWS[tk])
    # Global/overnight markets — deterministic so the golden is hermetic.
    monkeypatch.setattr(sources, "recent_change",
                        lambda sym: {"last": 100.0, "prev_close": 102.0, "as_of_date": "2026-06-09"})
    monkeypatch.setattr(sources, "recommendation_trend",
                        lambda tk: {"period": "2026-06-01", "strongBuy": 10, "buy": 5,
                                    "hold": 3, "sell": 1, "strongSell": 0})
    monkeypatch.setattr(price_targets, "fetch_target", lambda tk: TARGETS[tk])

    monkeypatch.setattr(store, "get_tickers", lambda: list(TICKERS))
    monkeypatch.setattr(store, "get_holdings",
                        lambda: {"AAA": {"shares": 10.0, "cost_basis": 90.0},
                                 "BBB": {"shares": 2.0, "cost_basis": 350.0}})
    monkeypatch.setattr(store, "get_latest_enriched", lambda: json.loads(json.dumps(PRIOR)))
    monkeypatch.setattr(store, "get_fundamentals",
                        lambda tk, earnings=None: dict(FUNDAMENTALS[tk]))
    monkeypatch.setattr(store, "get_market_extras", lambda tk: dict(EXTRAS[tk]))

    # The benchmark fetch goes through sources.price_history with cfg["benchmark"];
    # synth maps unknown tickers (SPY) to the BBB frame — deterministic either way.


def _normalize(snap: dict) -> dict:
    return json.loads(json.dumps(snap, default=str, sort_keys=True))


def _check_or_regen(snap: dict, name: str):
    FIXTURES.mkdir(exist_ok=True)
    golden_path = FIXTURES / f"golden_{name}.json"
    got = _normalize(snap)
    if os.environ.get("REGEN_GOLDEN") == "1":
        golden_path.write_text(json.dumps(got, indent=1, sort_keys=True))
        return
    assert golden_path.exists(), f"golden missing — REGEN_GOLDEN=1 pytest {__file__}"
    want = json.loads(golden_path.read_text())
    assert got == want, (
        f"snapshot drifted from golden_{name}.json — if intentional, regenerate with "
        f"REGEN_GOLDEN=1 and declare the changed keys in the phase commit"
    )


def test_golden_postclose(fake_world):
    _check_or_regen(snapshot.build_snapshot("postclose"), "postclose")


def test_golden_intraday(fake_world):
    _check_or_regen(snapshot.build_snapshot("intraday"), "intraday")
