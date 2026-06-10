from datetime import date

from tracker.quarterly import (
    Quarter,
    rev_qoq,
    gross_margin,
    gross_margin_qoq_pp,
    yoy_guarded,
    finite,
)


def q(pe, rev=None, eps=None, gp=None):
    return Quarter(period_end=date.fromisoformat(pe), revenue=rev, eps=eps, gross_profit=gp)


# AMAT-like, newest first
AMAT = [
    q("2026-04-30", rev=7910e6, eps=3.51, gp=3947e6),
    q("2026-01-31", rev=7012e6, eps=2.54, gp=3435e6),
    q("2025-10-31", rev=6800e6, eps=2.38, gp=3265e6),
    q("2025-07-31", rev=7302e6, eps=2.22, gp=3562e6),
    q("2025-04-30", rev=7100e6, eps=2.63, gp=3485e6),
]


def test_rev_qoq_basic():
    assert rev_qoq(AMAT) == round((7910 / 7012 - 1) * 100, 2)  # ~ +12.81


def test_rev_qoq_needs_two_quarters():
    assert rev_qoq(AMAT[:1]) is None


def test_rev_qoq_zero_prev():
    assert rev_qoq([q("2026-04-30", rev=100), q("2026-01-31", rev=0)]) is None


def test_gross_margin_percent():
    assert gross_margin(AMAT) == round(3947 / 7910 * 100, 2)  # ~ 49.9, not 0.499


def test_gross_margin_missing():
    assert gross_margin([q("2026-04-30", rev=100, gp=None)]) is None


def test_margin_qoq_in_points():
    # 49.9% - 49.0% ~= 0.9pp (a points difference, not a fraction)
    val = gross_margin_qoq_pp(AMAT)
    assert val is not None and 0.5 < val < 1.5


def test_margin_qoq_needs_two():
    assert gross_margin_qoq_pp(AMAT[:1]) is None


def test_margin_qoq_negative_when_margin_falls():
    # margin 46% this quarter vs 50% prior -> -4.0 points (a reversed subtraction would be +4)
    qs = [q("2026-04-30", rev=100.0, gp=46.0), q("2026-01-31", rev=100.0, gp=50.0)]
    assert gross_margin_qoq_pp(qs) == -4.0


def test_yoy_revenue_basic():
    assert yoy_guarded(AMAT, "revenue") == round((7910 / 7100 - 1) * 100, 2)  # ~ +11.4


def test_yoy_eps_basic():
    assert yoy_guarded(AMAT, "eps") == round((3.51 / 2.63 - 1) * 100, 2)  # ~ +33.5


def test_yoy_needs_five_quarters():
    assert yoy_guarded(AMAT[:4], "eps") is None


def test_yoy_eps_nonpositive_denominator_returns_none():
    # year-ago EPS was a loss -> a ratio would falsely read a sign; must be None
    qs = [
        q("2026-04-30", eps=0.10),
        q("2026-01-31", eps=0.05),
        q("2025-10-31", eps=0.0),
        q("2025-07-31", eps=-0.10),
        q("2025-04-30", eps=-0.20),
    ]
    assert yoy_guarded(qs, "eps") is None


def test_yoy_eps_tiny_denominator_returns_none():
    qs = [
        q("2026-04-30", eps=0.50),
        q("2026-01-31", eps=0.4),
        q("2025-10-31", eps=0.3),
        q("2025-07-31", eps=0.2),
        q("2025-04-30", eps=0.001),  # tiny -> explosive ratio -> None
    ]
    assert yoy_guarded(qs, "eps") is None


def test_yoy_eps_swing_to_loss_is_negative_not_positive():
    # current loss vs prior profit -> directionally negative (deterioration), never positive
    qs = [
        q("2026-04-30", eps=-0.40),
        q("2026-01-31", eps=0.08),
        q("2025-10-31", eps=0.06),
        q("2025-07-31", eps=0.17),
        q("2025-04-30", eps=0.20),
    ]
    v = yoy_guarded(qs, "eps")
    assert v is not None and v < 0


def test_unsorted_input_is_sorted_newest_first():
    shuffled = [AMAT[2], AMAT[0], AMAT[4], AMAT[1], AMAT[3]]
    assert rev_qoq(shuffled) == rev_qoq(AMAT)
    assert yoy_guarded(shuffled, "revenue") == yoy_guarded(AMAT, "revenue")


def test_finite_scrubs_nan_inf_bool():
    assert finite(float("nan")) is None
    assert finite(float("inf")) is None
    assert finite(True) is None
    assert finite(3.5) == 3.5


def test_nan_cells_treated_as_missing():
    qs = [q("2026-04-30", rev=float("nan")), q("2026-01-31", rev=7012e6)]
    assert rev_qoq(qs) is None


# ── P4: gross margin YoY (pp) — the seasonality corroboration ────────────

def test_gross_margin_yoy_pp_math():
    from tracker.quarterly import gross_margin_yoy_pp
    qs = [
        q("2026-04-30", rev=100e6, gp=50e6),   # 50% margin
        q("2026-01-31", rev=95e6, gp=49e6),
        q("2025-10-31", rev=90e6, gp=46e6),
        q("2025-07-31", rev=85e6, gp=43e6),
        q("2025-04-30", rev=80e6, gp=42e6),    # 52.5% a year ago
    ]
    assert gross_margin_yoy_pp(qs) == -2.5


def test_gross_margin_yoy_pp_needs_five_quarters():
    from tracker.quarterly import gross_margin_yoy_pp
    qs = [q("2026-04-30", rev=100e6, gp=50e6)] * 4
    assert gross_margin_yoy_pp(qs) is None


def test_gross_margin_yoy_pp_missing_gp_is_none():
    from tracker.quarterly import gross_margin_yoy_pp
    qs = [
        q("2026-04-30", rev=100e6, gp=50e6),
        q("2026-01-31", rev=95e6, gp=49e6),
        q("2025-10-31", rev=90e6, gp=46e6),
        q("2025-07-31", rev=85e6, gp=43e6),
        q("2025-04-30", rev=80e6, gp=None),    # year-ago margin unknown
    ]
    assert gross_margin_yoy_pp(qs) is None


def test_record_from_quarters_includes_margin_yoy():
    from tracker.quarterly import record_from_quarters
    qs = [
        q("2026-04-30", rev=100e6, gp=50e6),
        q("2026-01-31", rev=95e6, gp=49e6),
        q("2025-10-31", rev=90e6, gp=46e6),
        q("2025-07-31", rev=85e6, gp=43e6),
        q("2025-04-30", rev=80e6, gp=42e6),
    ]
    rec = record_from_quarters(qs)
    assert rec["gross_margin_yoy_pp"] == -2.5
