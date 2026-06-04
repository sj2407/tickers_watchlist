"""P4 gate: thesis-break flags toggle on boundaries and never false-positive
on missing data."""
from tracker import thesis


def test_flags_fire_on_deterioration():
    fund = {"revenue_qoq_pct": -6.0, "gross_margin_qoq_pp": -3.0, "eps_miss_count_last3": 2}
    f = thesis.thesis_break_flags(fund)
    assert f["revenue_qoq_drop"] is True
    assert f["margin_compression"] is True
    assert f["repeated_eps_miss"] is True
    assert f["any"] is True


def test_flags_quiet_when_healthy():
    fund = {"revenue_qoq_pct": 4.0, "gross_margin_qoq_pp": 0.5, "eps_miss_count_last3": 1}
    f = thesis.thesis_break_flags(fund)
    assert f["revenue_qoq_drop"] is False
    assert f["margin_compression"] is False
    assert f["repeated_eps_miss"] is False
    assert f["any"] is False


def test_boundaries_are_inclusive():
    # exactly at threshold should fire (<=)
    f = thesis.thesis_break_flags({"revenue_qoq_pct": -5.0, "gross_margin_qoq_pp": -2.0,
                                   "eps_miss_count_last3": 2})
    assert f["revenue_qoq_drop"] is True
    assert f["margin_compression"] is True
    assert f["repeated_eps_miss"] is True


def test_missing_data_is_none_not_false():
    f = thesis.thesis_break_flags({})  # nothing known
    assert f["revenue_qoq_drop"] is None
    assert f["margin_compression"] is None
    assert f["repeated_eps_miss"] is None
    assert f["any"] is False  # no TRUE flag → no break asserted


def test_none_fund_is_safe():
    f = thesis.thesis_break_flags(None)
    assert f["any"] is False
