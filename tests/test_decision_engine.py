"""P5 gate — the go/no-go. Covers every truth-table row of provisional_lean
plus the invariants that encode the user's rules (esp. C1: size never matters)."""
import pytest

from tracker import signals, metrics

CFG = {"signals": {"rsi_overbought": 70, "rsi_oversold": 30,
                   "extended_above_sma20_pct": 12.0, "earnings_soon_days": 7}}


def mk(held=True, shares=1.0, weight=5.0, trend="uptrend", ma_cross="above",
       rsi=50.0, d20=2.0, rs20=1.0, rev_yoy=20.0, eps_yoy=20.0, days=30,
       tb=None):
    return {
        "technicals": {"trend": trend, "ma_cross": ma_cross, "rsi14": rsi, "dist_sma20_pct": d20},
        "position": {"held": held, "shares": shares, "weight_pct": weight},
        "earnings": {"days_until_next": days},
        "fundamentals": {"revenue_yoy": rev_yoy, "eps_yoy": eps_yoy},
        "relative_strength": {"rs20d": rs20},
        "thesis_break": tb or {"revenue_qoq_drop": False, "margin_compression": False,
                               "repeated_eps_miss": False, "any": False},
    }


def lean(t):
    return signals.provisional_lean(t, CFG)["lean"]


# ── truth-table rows ────────────────────────────────────────────────────

def test_not_held_is_watch():
    assert lean(mk(held=False, shares=0)) == "watch"


def test_strength_and_room_is_pile_on():
    assert lean(mk()) == "pile_on"


def test_clear_break_two_thesis_flags_is_exit():
    tb = {"revenue_qoq_drop": True, "margin_compression": True,
          "repeated_eps_miss": False, "any": True}
    assert lean(mk(tb=tb)) == "exit"


def test_deterioration_confluence_is_trim():
    # downtrend + negative relative strength = 2 deterioration signals, no clean break
    assert lean(mk(trend="downtrend", ma_cross="below", rs20=-3.0)) == "trim"


def test_default_otherwise_is_hold():
    # mixed trend, nothing strong, single-or-no deterioration
    assert lean(mk(trend="mixed", ma_cross="below", rs20=0.5, rev_yoy=10)) == "hold"


# ── invariants (the rules the user cares about) ─────────────────────────

def test_dont_chase_overbought_is_hold_not_pileon_not_trim():
    out = lean(mk(rsi=78.0))           # strong but overbought
    assert out == "hold"


def test_single_mild_negative_is_hold_not_trim():
    # only ONE deterioration signal (downtrend) → not enough for a trim
    assert lean(mk(trend="downtrend", ma_cross="below", rs20=1.0, rev_yoy=20)) == "hold"


def test_no_sizing_into_a_print():
    assert lean(mk(days=1)) == "hold"          # would-be pile_on, but reports tomorrow
    assert lean(mk(days=0)) == "hold"


def test_C1_position_size_never_changes_the_lean():
    """The core rule: weight/% of book has zero influence."""
    assert lean(mk(weight=5.0)) == lean(mk(weight=90.0))
    # a healthy name that happens to be 90% of the sleeve is NOT trimmed/exited
    assert lean(mk(weight=90.0)) in ("pile_on", "hold")
    assert lean(mk(weight=95.0, trend="downtrend", ma_cross="below", rs20=-3.0)) == "trim"  # deterioration, not size


def test_determinism():
    assert lean(mk()) == lean(mk())


# ── glossary linkage ────────────────────────────────────────────────────

def test_referenced_keys_all_exist_in_registry():
    missing = signals.REFERENCED_KEYS - metrics.all_keys()
    assert not missing, f"engine references metrics not in the registry: {missing}"
