"""Tests for tracker.price_targets — the analyst price-target fetcher.

We don't hit the network: we monkeypatch yfinance's .info so the guard logic
(missing/NaN/non-positive handling, degenerate ranges) is what's under test.
"""
from __future__ import annotations

import math

import tracker.price_targets as pt


def test_pos_filters_bad_values():
    assert pt._pos(286.5) == 286.5
    assert pt._pos("180") == 180.0
    assert pt._pos(None) is None
    assert pt._pos(0) is None
    assert pt._pos(-5) is None
    assert pt._pos(float("nan")) is None
    assert pt._pos("n/a") is None


class _FakeTicker:
    def __init__(self, info):
        self.info = info


def _patch(monkeypatch, info):
    monkeypatch.setattr(pt.yf, "Ticker", lambda _t: _FakeTicker(info))


def test_full_target(monkeypatch):
    _patch(monkeypatch, {
        "targetLowPrice": 180.0, "targetMedianPrice": 286.5,
        "targetMeanPrice": 298.07, "targetHighPrice": 500.0,
        "numberOfAnalystOpinions": 58,
    })
    out = pt.fetch_target("NVDA")
    assert out == {"low": 180.0, "median": 286.5, "mean": 298.07,
                   "high": 500.0, "num_analysts": 58, "source": "yfinance"}


def test_median_only_is_enough(monkeypatch):
    _patch(monkeypatch, {
        "targetLowPrice": 21.0, "targetMedianPrice": 25.0,
        "targetMeanPrice": None, "targetHighPrice": 35.0,
        "numberOfAnalystOpinions": 14,
    })
    out = pt.fetch_target("HIMS")
    assert out is not None and out["median"] == 25.0 and out["mean"] is None


def test_none_when_no_range(monkeypatch):
    _patch(monkeypatch, {"targetMeanPrice": 100.0})  # no low/high
    assert pt.fetch_target("X") is None


def test_none_when_no_central_estimate(monkeypatch):
    _patch(monkeypatch, {"targetLowPrice": 10.0, "targetHighPrice": 20.0})
    assert pt.fetch_target("X") is None


def test_none_when_inverted_range(monkeypatch):
    _patch(monkeypatch, {
        "targetLowPrice": 50.0, "targetHighPrice": 20.0, "targetMedianPrice": 30.0,
    })
    assert pt.fetch_target("X") is None


def test_none_on_fetch_error(monkeypatch):
    def boom(_t):
        raise RuntimeError("network")
    monkeypatch.setattr(pt.yf, "Ticker", boom)
    assert pt.fetch_target("X") is None
