"""P4 gate: thesis-break flags toggle on boundaries and never false-positive
on missing data."""
from tracker import thesis


def test_flags_fire_on_deterioration():
    # P4 declared edit: mild margin QoQ now needs YoY-margin corroboration (≤ 0)
    # — fixture gains the field, the assertion is UNCHANGED (still True).
    fund = {"revenue_qoq_pct": -6.0, "gross_margin_qoq_pp": -3.0,
            "gross_margin_yoy_pp": -1.0, "eps_miss_count_last3": 2}
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
    # exactly at threshold should fire (<=); margin YoY at exactly 0.0 corroborates (≤ 0)
    f = thesis.thesis_break_flags({"revenue_qoq_pct": -5.0, "gross_margin_qoq_pp": -2.0,
                                   "gross_margin_yoy_pp": 0.0, "eps_miss_count_last3": 2})
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


def test_margin_compression_suppressed_for_hypergrowth():
    """A small sequential margin dip is noise when revenue is growing fast — don't flag it."""
    fund = {"gross_margin_qoq_pp": -3.0, "gross_margin_yoy_pp": -1.0, "revenue_yoy": 100.0}
    f = thesis.thesis_break_flags(fund)
    assert f["margin_compression"] is False


def test_margin_compression_fires_when_growth_is_weak():
    """The same margin dip IS a flag when growth isn't there to excuse it."""
    fund = {"gross_margin_qoq_pp": -3.0, "gross_margin_yoy_pp": -0.5, "revenue_yoy": 5.0}
    f = thesis.thesis_break_flags(fund)
    assert f["margin_compression"] is True


def test_severe_margin_collapse_is_never_suppressed():
    """A −17pp collapse (OUST-like) is real deterioration even at high growth."""
    fund = {"gross_margin_qoq_pp": -17.0, "revenue_yoy": 49.0}
    f = thesis.thesis_break_flags(fund)
    assert f["margin_compression"] is True


# ── P4: seasonality awareness (mild QoQ needs YoY-margin corroboration) ──

def test_mild_dip_with_margin_down_yoy_flags():
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -2.5, "gross_margin_yoy_pp": -1.0,
                                   "revenue_yoy": 5.0})
    assert f["margin_compression"] is True


def test_mild_dip_but_margin_up_yoy_is_seasonal_no_flag():
    """The seasonal case: margin dipped vs LAST quarter but is HIGHER than the same
    quarter last year — mix, not deterioration."""
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -2.5, "gross_margin_yoy_pp": +2.0,
                                   "revenue_yoy": 5.0})
    assert f["margin_compression"] is False


def test_mild_dip_without_yoy_history_is_insufficient_not_a_flag():
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -2.5, "revenue_yoy": 5.0})
    assert f["margin_compression"] is None  # insufficient corroboration, never a flag
    assert f["any"] is False


def test_severe_collapse_ignores_positive_yoy():
    # severe at exactly the −5.0 boundary, YoY positive: still flags.
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -5.0, "gross_margin_yoy_pp": +3.0,
                                   "revenue_yoy": 5.0})
    assert f["margin_compression"] is True


def test_hypergrowth_suppression_still_applies_after_corroboration():
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -2.5, "gross_margin_yoy_pp": -1.0,
                                   "revenue_yoy": 100.0})
    assert f["margin_compression"] is False  # corroborated mild, but hypergrowth noise


# ── P4b input: severity is exposed by thesis, never re-derived elsewhere ──

def test_margin_severe_exposed():
    assert thesis.thesis_break_flags({"gross_margin_qoq_pp": -6.0})["margin_severe"] is True
    assert thesis.thesis_break_flags({"gross_margin_qoq_pp": -2.5,
                                      "gross_margin_yoy_pp": -1.0})["margin_severe"] is False
    assert thesis.thesis_break_flags({})["margin_severe"] is None


def test_margin_severe_does_not_count_toward_any():
    # 'any' is about the three core flags; the severity qualifier must not
    # independently assert a break.
    f = thesis.thesis_break_flags({"gross_margin_qoq_pp": -1.0})  # not even mild
    assert f["margin_severe"] is False and f["any"] is False
