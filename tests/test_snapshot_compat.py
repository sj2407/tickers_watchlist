"""P0 backward-compat gate: a REAL pre-v3 snapshot (trimmed from production,
2026-06-10 — it even contains the live watch-on-held bug) must keep flowing through
the pipeline's merge / signal / trigger layers with concrete, correct outcomes.
Later phases add fields; they must never make old payloads error or change meaning.
"""
import json
from pathlib import Path

import pytest

from tracker import signals, triggers
from tracker.snapshot import merge_narrative, NARRATIVE_TICKER_FIELDS
from tracker.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "prev3_snapshot.json"


@pytest.fixture(scope="module")
def prev3():
    return json.loads(FIXTURE.read_text())


def test_fixture_is_genuinely_pre_v3(prev3):
    t = prev3["tickers"][0]
    assert "rs_trend" not in t["relative_strength"]          # P3 field absent
    assert "narrative_freshness" not in t                     # P8 field absent
    assert "revenue_yoy_q" not in (t.get("fundamentals") or {})  # P7 field absent


def test_carry_forward_from_prev3_prior(prev3):
    blank = {f: None for f in NARRATIVE_TICKER_FIELDS}
    fresh = {"tickers": [{"ticker": t["ticker"], **blank} for t in prev3["tickers"]],
             "market_recap": None, "macro_context": None}
    merge_narrative(fresh, prev3)
    hims = next(t for t in fresh["tickers"] if t["ticker"] == "HIMS")
    src = next(t for t in prev3["tickers"] if t["ticker"] == "HIMS")
    assert hims["takeaway"] == src["takeaway"] and hims["takeaway"] is not None
    assert hims["final_lean"] == src["final_lean"]  # pre-P2: carried verbatim, even 'watch'
    assert fresh["market_recap"] == prev3["market_recap"] is not None


def test_signals_recompute_on_prev3_rows(prev3):
    cfg = load_config()
    for t in prev3["tickers"]:
        out = signals.build_signals(t, cfg)
        assert out["provisional_lean"] in ("pile_on", "hold", "trim", "watch")
        assert isinstance(out["badges"], list)


def test_triggers_run_on_prev3_rows(prev3):
    cfg = load_config()
    for t in prev3["tickers"]:
        trigs = triggers.compute_triggers(t, cfg)
        assert isinstance(trigs, list)
        assert all(x in ("entry_zone", "notable_dip") for x in trigs)
