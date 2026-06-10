"""P2 gate: the routine's lean vocabulary is ENFORCED, not trusted.

Live bug being fixed: the routine wrote final_lean="watch" on four HELD names
(two of them hiding quant trim proposals). Rules:
- held  + "watch"                          -> coerced to "hold", lean_coerced_from set
- held  + junk (not pile_on/hold/trim/exit) -> provisional lean, lean_rejected set
- not held + anything but watch/hold        -> coerced to "watch", lean_coerced_from set
- valid leans pass through untouched
Validation runs post-merge on ALL rows (enrich AND pipeline), so carried-forward
bad leans heal without waiting on the LLM.
"""
import json

import pytest

from tracker import signals, triggers
from tracker.signals import validate_leans
from tracker.snapshot import merge_narrative, NARRATIVE_TICKER_FIELDS


def _row(ticker="AAA", held=True, lean="hold", provisional="hold"):
    return {
        "ticker": ticker,
        "position": {"held": held, "shares": 10.0 if held else 0},
        "final_lean": lean,
        "signals": {"provisional_lean": provisional},
        "technicals": {}, "thesis_break": {}, "price": {},
    }


def _snap(*rows):
    return {"tickers": list(rows)}


def test_watch_on_held_coerced_to_hold():
    s = _snap(_row(lean="watch"))
    validate_leans(s)
    t = s["tickers"][0]
    assert t["final_lean"] == "hold"
    assert t["lean_coerced_from"] == "watch"


def test_junk_on_held_falls_back_to_provisional():
    s = _snap(_row(lean="strong_buy", provisional="trim"))
    validate_leans(s)
    t = s["tickers"][0]
    assert t["final_lean"] == "trim"
    assert t["lean_rejected"] == "strong_buy"


def test_valid_leans_pass_through_untouched():
    for lean in ("pile_on", "hold", "trim", "exit"):
        s = _snap(_row(lean=lean))
        validate_leans(s)
        t = s["tickers"][0]
        assert t["final_lean"] == lean
        assert not t.get("lean_coerced_from") and not t.get("lean_rejected")


def test_none_lean_left_alone_pre_narrative():
    s = _snap(_row(lean=None))
    validate_leans(s)
    assert s["tickers"][0]["final_lean"] is None


def test_watch_on_non_held_preserved():
    s = _snap(_row(held=False, lean="watch"))
    validate_leans(s)
    assert s["tickers"][0]["final_lean"] == "watch"
    assert not s["tickers"][0].get("lean_coerced_from")


def test_sizing_action_on_non_held_coerced_to_watch():
    s = _snap(_row(held=False, lean="pile_on"))
    validate_leans(s)
    t = s["tickers"][0]
    assert t["final_lean"] == "watch"
    assert t["lean_coerced_from"] == "pile_on"


def test_carried_forward_watch_on_held_heals_without_llm():
    # The pipeline path: a prior snapshot with the bad lean -> merge -> validate.
    prior = {"tickers": [{"ticker": "HIMS", "takeaway": "x", "final_lean": "watch"}]}
    fresh = _snap({**_row(ticker="HIMS", lean=None), "takeaway": None})
    for f in NARRATIVE_TICKER_FIELDS:
        fresh["tickers"][0].setdefault(f, None)
    merge_narrative(fresh, prior)
    assert fresh["tickers"][0]["final_lean"] == "watch"  # carried verbatim
    validate_leans(fresh)
    assert fresh["tickers"][0]["final_lean"] == "hold"   # healed
    assert fresh["tickers"][0]["lean_coerced_from"] == "watch"


def test_coercion_flag_survives_carry_forward():
    assert "lean_coerced_from" in NARRATIVE_TICKER_FIELDS
    prior = {"tickers": [{"ticker": "AAA", "final_lean": "hold", "lean_coerced_from": "watch"}]}
    fresh = _snap(_row(lean=None))
    for f in NARRATIVE_TICKER_FIELDS:
        fresh["tickers"][0].setdefault(f, None)
    merge_narrative(fresh, prior)
    assert fresh["tickers"][0]["lean_coerced_from"] == "watch"


def test_coercion_unfreezes_intraday_entry_triggers():
    """A held name stuck on 'watch' was entry-frozen (triggers need pile_on/hold);
    after coercion it participates again — intended, pinned here."""
    cfg = {"signals": {"rsi_overbought": 70},
           "intraday": {"near_support_pct": 2.0, "rsi_buy_band": 45.0,
                        "sma50_zone_low": -4.0, "sma50_zone_high": 1.0,
                        "notable_dip_pct": -5.0}}
    row = {
        "ticker": "AAA",
        "position": {"held": True, "shares": 10.0},
        "final_lean": "watch",
        "signals": {"provisional_lean": "trim"},  # fallback must not unfreeze it
        "technicals": {"rsi14": 40.0, "support_dist_pct": 1.0},
        "thesis_break": {"any": False},
        "price": {"day_change_pct": -1.0},
    }
    assert triggers.compute_triggers(row, cfg) == []  # frozen by 'watch'
    s = _snap(row)
    validate_leans(s)
    assert triggers.compute_triggers(s["tickers"][0], cfg) == ["entry_zone"]


def test_apply_enrichment_validates_all_rows(tmp_path, monkeypatch):
    """End-to-end through enrich: the overlay narrates only AAA, but the carried
    bad lean on BBB (absent from the overlay) is healed too."""
    from tracker import enrich, store

    snap = _snap(
        {**_row(ticker="AAA", lean="watch"), "takeaway": None},
        {**_row(ticker="BBB", lean="watch"), "takeaway": None},
    )
    snap["market_recap"] = None
    snap["as_of_date"] = "2026-06-09"
    snap["generated_at"] = "2026-06-09T17:00:00-04:00"
    sp = tmp_path / "snapshot.json"
    ep = tmp_path / "enrichment.json"
    sp.write_text(json.dumps(snap))
    ep.write_text(json.dumps({"market": {"recap": "R"},
                              "tickers": {"AAA": {"final_lean": "pile_on", "takeaway": "t"}}}))
    published = {}
    monkeypatch.setattr(store, "publish_enriched", lambda s, sid=None: published.update(s))

    out = enrich.apply_enrichment(sp, ep)
    a = next(t for t in out["tickers"] if t["ticker"] == "AAA")
    b = next(t for t in out["tickers"] if t["ticker"] == "BBB")
    assert a["final_lean"] == "pile_on" and not a.get("lean_coerced_from")
    assert b["final_lean"] == "hold" and b["lean_coerced_from"] == "watch"
    assert published.get("market_recap") == "R"  # still publishes


def test_routine_overwrite_clears_old_coercion_flag(tmp_path, monkeypatch):
    from tracker import enrich, store

    snap = _snap({**_row(ticker="AAA", lean="hold"), "takeaway": None,
                  "lean_coerced_from": "watch"})  # carried from an earlier coercion
    snap["market_recap"] = None
    snap["as_of_date"] = "2026-06-09"
    snap["generated_at"] = "2026-06-09T17:00:00-04:00"
    sp = tmp_path / "snapshot.json"
    ep = tmp_path / "enrichment.json"
    sp.write_text(json.dumps(snap))
    ep.write_text(json.dumps({"tickers": {"AAA": {"final_lean": "trim"}}}))
    monkeypatch.setattr(store, "publish_enriched", lambda s, sid=None: None)

    out = enrich.apply_enrichment(sp, ep)
    a = out["tickers"][0]
    assert a["final_lean"] == "trim"
    assert not a.get("lean_coerced_from")  # routine wrote a real lean; flag cleared


def test_failed_price_fetch_never_rewrites_a_stored_lean():
    """Review R1-3: position_math emits {"held": True} with NO shares key when
    the price fetch failed — that's still a held name; a degraded run must not
    coerce its stored trim to 'watch'."""
    s = _snap({"ticker": "AAA", "position": {"held": True},  # no shares key
               "final_lean": "trim", "signals": {"provisional_lean": "trim"},
               "technicals": {}, "thesis_break": {}, "price": {}})
    validate_leans(s)
    t = s["tickers"][0]
    assert t["final_lean"] == "trim"
    assert not t.get("lean_coerced_from") and not t.get("lean_rejected")
