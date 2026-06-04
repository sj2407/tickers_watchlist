"""P3 gate: fundamentals math is correct on injected data, and degrades
gracefully (no network in these tests)."""
from tracker import fundamentals as fnd


def _income(revs, epss, gps):
    """Build an FMP-like income list (newest quarter first)."""
    return [
        {"date": f"2026-{12 - i:02d}-31", "period": f"Q{i}", "revenue": revs[i],
         "eps": epss[i], "grossProfit": gps[i]}
        for i in range(len(revs))
    ]


def test_yoy_qoq_margin_and_ttm():
    # 5 quarters newest-first: rev grows YoY, dips QoQ; margins fall QoQ
    revs = [110.0, 120.0, 100.0, 95.0, 90.0]   # q0=110, q1=120 (QoQ down), q4=90 (YoY up)
    epss = [1.10, 1.20, 1.00, 0.95, 0.90]
    gps = [44.0, 60.0, 50.0, 47.5, 45.0]       # gm0=40%, gm1=50% -> -10pp QoQ
    out = fnd.compute("TEST", income=_income(revs, epss, gps), surprises=[])
    assert out["source"] == "injected"
    assert out["revenue_yoy"] == round((110 / 90 - 1) * 100, 1)
    assert out["eps_yoy"] == round((1.10 / 0.90 - 1) * 100, 1)
    assert out["revenue_qoq_pct"] == round((110 / 120 - 1) * 100, 1)
    assert out["gross_margin"] == 40.0
    assert out["gross_margin_qoq_pp"] == -10.0
    assert out["eps_ttm"] == round(1.10 + 1.20 + 1.00 + 0.95, 4)


def test_repeated_eps_miss_counts_last_three():
    surprises = [
        {"actualEarningResult": 0.9, "estimatedEarning": 1.0},   # miss
        {"actualEarningResult": 1.1, "estimatedEarning": 1.0},   # beat
        {"actualEarningResult": 0.8, "estimatedEarning": 1.0},   # miss
        {"actualEarningResult": 0.7, "estimatedEarning": 1.0},   # (older, ignored)
    ]
    out = fnd.compute("TEST", income=_income([100, 100, 100, 100, 100],
                                             [1, 1, 1, 1, 1], [50] * 5),
                      surprises=surprises)
    assert out["eps_miss_count_last3"] == 2


def test_empty_input_is_safe():
    out = fnd.compute("TEST", income=[], surprises=[])
    assert out["source"] in (None, "injected")
    assert out["revenue_yoy"] is None and out["gross_margin"] is None
    assert out["eps_miss_count_last3"] is None


def test_short_history_no_yoy_but_has_latest():
    out = fnd.compute("TEST", income=_income([100, 95], [1.0, 0.9], [50, 50]), surprises=[])
    assert out["revenue"] == 100.0
    assert out["revenue_yoy"] is None       # < 5 quarters
    assert out["revenue_qoq_pct"] == round((100 / 95 - 1) * 100, 1)
