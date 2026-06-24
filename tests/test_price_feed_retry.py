"""yfinance price-feed resilience (the 'whole board went blank' incident): a
transient Yahoo failure must be retried, not silently turned into an empty frame
that nulls every price/return/RS on the board."""
import pandas as pd
import pytest

from tracker import sources


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(sources.time, "sleep", lambda *_: None)


def _frame():
    idx = pd.to_datetime(["2026-06-22", "2026-06-23"])
    return pd.DataFrame(
        {"Open": [10, 11], "High": [11, 12], "Low": [9, 10], "Close": [10.5, 11.5],
         "Volume": [100, 110]}, index=idx)


class _Ticker:
    """yfinance stub: fails `fail_times` then returns a frame (or raises)."""
    def __init__(self, fail_times, mode="empty"):
        self.fail_times = fail_times
        self.mode = mode
        self.calls = 0

    def history(self, **_):
        self.calls += 1
        if self.calls <= self.fail_times:
            if self.mode == "raise":
                raise RuntimeError("rate limited")
            return pd.DataFrame()  # Yahoo's transient empty
        return _frame()


def test_history_retries_then_succeeds(monkeypatch):
    tk = _Ticker(fail_times=2, mode="empty")
    monkeypatch.setattr(sources.yf, "Ticker", lambda *_: tk)
    df = sources._yf_history("AAPL", "5d")
    assert not df.empty and tk.calls == 3  # 2 empty, 3rd good


def test_history_retries_on_exception(monkeypatch):
    tk = _Ticker(fail_times=1, mode="raise")
    monkeypatch.setattr(sources.yf, "Ticker", lambda *_: tk)
    df = sources._yf_history("AAPL", "5d")
    assert not df.empty and tk.calls == 2


def test_history_gives_up_after_three(monkeypatch):
    tk = _Ticker(fail_times=99, mode="empty")
    monkeypatch.setattr(sources.yf, "Ticker", lambda *_: tk)
    df = sources._yf_history("AAPL", "5d")
    assert df.empty and tk.calls == 3  # bounded, not infinite


def test_recent_change_rides_a_blip(monkeypatch):
    tk = _Ticker(fail_times=1, mode="empty")
    monkeypatch.setattr(sources.yf, "Ticker", lambda *_: tk)
    out = sources.recent_change("^KS11")
    assert out is not None and out["last"] == 11.5 and out["prev_close"] == 10.5


# --- last-known-good fallback (never publish a blank board) -------------------
from tracker import snapshot  # noqa: E402

_PRIOR = {
    "generated_at": "2026-06-23T16:30:00-04:00",
    "tickers": [{
        "ticker": "AAA",
        "price": {"last": 100.0, "prev_close": 98.0, "day_change_pct": 2.04},
        "returns": {"r1d": 2.0}, "relative_strength": {"rs20d": 1.5},
        "technicals": {"rsi14": 55.0}, "series": [{"d": "2026-06-23", "c": 100.0}],
    }],
}


def test_carry_forward_fills_blank_history_and_flags_stale_price():
    # Both live sources were down → price 'carried'; history empty this run.
    rows = [{"ticker": "AAA", "price": {"last": None}, "returns": {"r1d": None},
             "relative_strength": {"rs20d": None}, "technicals": {}, "series": []}]
    snapshot.carry_forward_quant(rows, _PRIOR, {"AAA": "carried"})
    r = rows[0]
    assert r["series"] and r["returns"]["r1d"] == 2.0 and r["relative_strength"]["rs20d"] == 1.5
    assert r["price"]["last"] == 100.0              # price block carried
    assert r["price_stale"] is True and r["priced_as_of"] == _PRIOR["generated_at"]
    assert r["series_carried"] is True


def test_live_price_keeps_fresh_price_but_carries_eod_blocks():
    # Finnhub gave a LIVE last price; only the daily-bar history was unavailable.
    rows = [{"ticker": "AAA", "price": {"last": 101.5, "prev_close": 98.0}, "returns": {},
             "relative_strength": {}, "technicals": {}, "series": []}]
    snapshot.carry_forward_quant(rows, _PRIOR, {"AAA": "finnhub"})
    r = rows[0]
    assert r["price"]["last"] == 101.5             # live price NOT overwritten
    assert "price_stale" not in r                   # not flagged stale
    assert r["series_carried"] is True and r["returns"]["r1d"] == 2.0  # EOD blocks carried
