"""Phase 6 gate: intraday entry-watch triggers — fire on the right dips, never on
up-moves / overbought / deteriorating names."""
from tracker import triggers, sources

CFG = {
    "intraday": {"near_support_pct": 2.0, "rsi_buy_band": 45.0,
                 "sma50_zone_low": -4.0, "sma50_zone_high": 1.0, "notable_dip_pct": -5.0},
    "signals": {"rsi_overbought": 70},
}


def row(lean="pile_on", thesis_any=False, day=-1.0, rsi=42.0, support_dist=1.0,
        d50=None, held=True, shares=1.0, final_lean=None):
    return {
        "position": {"held": held, "shares": shares},
        "technicals": {"rsi14": rsi, "support_dist_pct": support_dist, "dist_sma50_pct": d50},
        "thesis_break": {"any": thesis_any},
        "signals": {"provisional_lean": lean},
        "final_lean": final_lean,
        "price": {"day_change_pct": day},
    }


def test_entry_zone_fires_on_dip_near_support():
    assert "entry_zone" in triggers.compute_triggers(row(), CFG)


def test_rsi_cooled_alone_fires_entry():
    assert "entry_zone" in triggers.compute_triggers(row(support_dist=None, d50=None, rsi=40.0), CFG)


def test_no_entry_on_an_up_day():
    assert triggers.compute_triggers(row(day=2.0)) if False else triggers.compute_triggers(row(day=2.0), CFG) == []


def test_no_entry_when_overbought():
    assert "entry_zone" not in triggers.compute_triggers(row(rsi=75.0), CFG)


def test_no_entry_for_trim_or_exit_lean():
    assert triggers.compute_triggers(row(lean="trim"), CFG) == []
    assert triggers.compute_triggers(row(lean="exit"), CFG) == []


def test_no_trigger_when_thesis_broken():
    assert triggers.compute_triggers(row(thesis_any=True, day=-6.0), CFG) == []


def test_notable_dip_fires_on_big_drop_thesis_intact():
    out = triggers.compute_triggers(row(lean="hold", day=-6.0, rsi=60.0, support_dist=None), CFG)
    assert "notable_dip" in out


def test_nothing_when_no_setup():
    assert triggers.compute_triggers(row(rsi=60.0, support_dist=None, d50=10.0, day=-0.2), CFG) == []


def test_final_lean_overrides_provisional():
    # quant says pile_on but routine set exit → no entry trigger
    assert triggers.compute_triggers(row(lean="pile_on", final_lean="exit"), CFG) == []


def test_call_counter_resets():
    sources.reset_finnhub_calls()
    assert sources.finnhub_call_count() == 0
