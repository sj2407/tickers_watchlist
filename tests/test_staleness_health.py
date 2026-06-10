"""P8 gate: narrative age and data health are VISIBLE.

If the routine fails silently, days-old prose used to sit beside fresh numbers
with no indication; failed fetches rendered identically to "no news". Now every
ticker carries narrative_as_of + a tri-state narrative_freshness (computed in
tested Python, the web is purely presentational), and the snapshot carries a
data_health block with fetch-failure counts.
"""
import json
from datetime import date

import pytest

from tracker import enrich, snapshot, sources, store
from tracker.snapshot import narrative_freshness, NARRATIVE_TICKER_FIELDS

GEN = "2026-06-09T17:00:00-04:00"


# ── the tri-state helper (all boundaries) ────────────────────────────────

def test_fresh_when_stamped_at_or_after_generation():
    assert narrative_freshness("2026-06-09T17:05:00-04:00", GEN) == "fresh"
    assert narrative_freshness(GEN, GEN) == "fresh"


def test_carried_when_older_but_within_24h():
    assert narrative_freshness("2026-06-09T09:14:00-04:00", GEN) == "carried"
    assert narrative_freshness("2026-06-08T17:00:01-04:00", GEN) == "carried"  # 24h − 1s


def test_stale_beyond_24h():
    assert narrative_freshness("2026-06-08T16:59:59-04:00", GEN) == "stale"
    assert narrative_freshness("2026-06-05T17:00:00-04:00", GEN) == "stale"


def test_exactly_24h_is_carried_not_stale():
    assert narrative_freshness("2026-06-08T17:00:00-04:00", GEN) == "carried"


def test_no_stamp_or_garbage_is_none():
    assert narrative_freshness(None, GEN) is None
    assert narrative_freshness("not-a-date", GEN) is None
    assert narrative_freshness(GEN, None) is None


# ── stamps travel with the words ─────────────────────────────────────────

def test_narrative_as_of_is_a_carried_field():
    assert "narrative_as_of" in NARRATIVE_TICKER_FIELDS


def test_merge_narrative_carries_the_stamp():
    prior = {"tickers": [{"ticker": "AAA", "takeaway": "x",
                          "narrative_as_of": "2026-06-09T09:14:00-04:00"}]}
    fresh = {"tickers": [{"ticker": "AAA",
                          **{f: None for f in NARRATIVE_TICKER_FIELDS}}],
             "market_recap": None, "macro_context": None}
    snapshot.merge_narrative(fresh, prior)
    assert fresh["tickers"][0]["narrative_as_of"] == "2026-06-09T09:14:00-04:00"


def test_enrich_stamps_overlaid_and_grades_all(tmp_path, monkeypatch):
    snap = {
        "generated_at": GEN, "as_of_date": "2026-06-09", "market_recap": None,
        "tickers": [
            {"ticker": "AAA", "position": {"held": True, "shares": 1.0},
             "signals": {"provisional_lean": "hold"}, "final_lean": "hold",
             "takeaway": None, "narrative_as_of": None},
            {"ticker": "BBB", "position": {"held": True, "shares": 1.0},
             "signals": {"provisional_lean": "hold"}, "final_lean": "hold",
             "takeaway": "old words", "narrative_as_of": "2026-06-05T16:14:00-04:00"},
        ],
    }
    sp = tmp_path / "snapshot.json"
    ep = tmp_path / "enrichment.json"
    sp.write_text(json.dumps(snap))
    ep.write_text(json.dumps({"market": {"recap": "R"},
                              "tickers": {"AAA": {"takeaway": "new words"}}}))
    monkeypatch.setattr(store, "publish_enriched", lambda s, sid=None: None)

    out = enrich.apply_enrichment(sp, ep)
    a = next(t for t in out["tickers"] if t["ticker"] == "AAA")
    b = next(t for t in out["tickers"] if t["ticker"] == "BBB")
    assert a["narrative_as_of"] is not None and a["narrative_freshness"] == "fresh"
    assert b["narrative_as_of"] == "2026-06-05T16:14:00-04:00"  # untouched
    assert b["narrative_freshness"] == "stale"                  # 4 days old, graded
    assert out["market_narrative_as_of"] is not None


# ── finnhub failure counter ──────────────────────────────────────────────

def test_failure_counter_increments_and_resets(monkeypatch):
    monkeypatch.setattr(sources, "get_key", lambda name: "test-key")

    class Boom:
        def get(self, *a, **kw):
            raise OSError("network down")

    monkeypatch.setattr(sources, "_session", Boom())
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    sources.reset_finnhub_calls()
    assert sources._finnhub_get("/x", {}) is None
    assert sources.finnhub_failure_count() == 1
    assert sources.finnhub_call_count() == 1
    sources._finnhub_get("/x", {})
    assert sources.finnhub_failure_count() == 2
    sources.reset_finnhub_calls()
    assert sources.finnhub_failure_count() == 0


def test_junk_only_overlay_does_not_refresh_the_stamp(tmp_path, monkeypatch):
    """Review R1-2: an overlay entry with zero narrative fields must not bump
    narrative_as_of (the words didn't change — the stamp must not lie)."""
    old_stamp = "2026-06-05T16:14:00-04:00"
    snap = {
        "generated_at": GEN, "as_of_date": "2026-06-09", "market_recap": None,
        "tickers": [{"ticker": "AAA", "position": {"held": True, "shares": 1.0},
                     "signals": {"provisional_lean": "hold"}, "final_lean": "hold",
                     "takeaway": "old words", "narrative_as_of": old_stamp}],
    }
    sp = tmp_path / "snapshot.json"
    ep = tmp_path / "enrichment.json"
    sp.write_text(json.dumps(snap))
    ep.write_text(json.dumps({"tickers": {"AAA": {"junk_key": "x"}}}))
    monkeypatch.setattr(store, "publish_enriched", lambda s, sid=None: None)
    out = enrich.apply_enrichment(sp, ep)
    assert out["tickers"][0]["narrative_as_of"] == old_stamp
    assert out["tickers"][0]["narrative_freshness"] == "stale"
