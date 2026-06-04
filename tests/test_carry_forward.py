"""Phase 4 gate: narrative carry-forward never drops/nulls an output."""
from tracker.snapshot import merge_narrative, NARRATIVE_TICKER_FIELDS, NARRATIVE_TOP_FIELDS


def _fresh():
    blank = {f: None for f in NARRATIVE_TICKER_FIELDS}
    return {
        "tickers": [{"ticker": "AAA", **blank}, {"ticker": "BBB", **blank}],
        "market_recap": None, "macro_context": None,
    }


def _prior():
    return {
        "tickers": [{
            "ticker": "AAA", "takeaway": "t", "sentiment": "bullish",
            "catalyst_summary": "c", "earnings_recap": None, "final_lean": "pile_on",
            "rationale": "r", "entry_guidance": "e", "invalidation": "i",
        }],
        "market_recap": "MR", "macro_context": "MC",
    }


def test_carries_all_fields_and_top_level_for_matching_ticker():
    f = _fresh()
    merge_narrative(f, _prior())
    a = next(t for t in f["tickers"] if t["ticker"] == "AAA")
    assert a["takeaway"] == "t" and a["final_lean"] == "pile_on"
    assert a["entry_guidance"] == "e" and a["invalidation"] == "i"   # the fields §C had missed
    assert f["market_recap"] == "MR" and f["macro_context"] == "MC"  # top-level carried too


def test_ticker_absent_from_prior_stays_null_no_crash():
    f = _fresh()
    merge_narrative(f, _prior())
    b = next(t for t in f["tickers"] if t["ticker"] == "BBB")
    assert all(b[x] is None for x in NARRATIVE_TICKER_FIELDS)


def test_cold_start_prior_none_is_safe():
    f = _fresh()
    assert merge_narrative(f, None) is f
    assert f["market_recap"] is None


def test_does_not_overwrite_a_value_this_run_already_set():
    f = _fresh()
    f["tickers"][0]["final_lean"] = "exit"   # a value the current run produced
    merge_narrative(f, _prior())
    assert f["tickers"][0]["final_lean"] == "exit"  # current run wins; carry only fills nulls
