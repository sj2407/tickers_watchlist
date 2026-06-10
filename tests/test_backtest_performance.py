"""P10 gate: the backtest evaluator (no lookahead, n<30 honesty) and the
sleeve-performance math (time-weighted — contributions are NOT returns)."""
from datetime import date, timedelta

import pytest

from tracker import backtest, performance

# ── synthetic snapshot world ──────────────────────────────────────────────

DATES = [date(2026, 1, 5) + timedelta(days=i + (i // 5) * 2) for i in range(30)]  # weekdays-ish


def _snap(d, tickers):
    return {"generated_at": f"{d}T16:14:00-04:00", "as_of_date": d.isoformat(),
            "tickers": tickers}


def _tk(name, px, lean, dims=()):
    return {"ticker": name, "price": {"last": px}, "final_lean": lean,
            "signals": {"provisional_lean": lean, "drivers": {"deterioration": list(dims)}}}


def _world():
    """AAA: pile_on while rising 1%/session. BBB: trim (downtrend dim) while
    falling 1%/session. Benchmark: flat."""
    snaps = []
    for i, d in enumerate(DATES):
        snaps.append(_snap(d, [
            _tk("AAA", 100.0 * (1.01 ** i), "pile_on"),
            _tk("BBB", 100.0 * (0.99 ** i), "trim", dims=["downtrend"]),
        ]))
    bench = {d: 100.0 for d in DATES}
    return snaps, bench


def test_fwd_uses_strictly_later_dates_only():
    prices = {DATES[i]: 100.0 + i for i in range(10)}
    assert backtest._fwd(prices, DATES[0], 1) == pytest.approx(1.0)   # next session
    assert backtest._fwd(prices, DATES[9], 1) is None                 # end of history
    assert backtest._fwd(prices, DATES[5], 5) is None                 # no shortened window
    assert backtest._fwd(prices, DATES[4], 5) == pytest.approx(109 / 104 * 100 - 100, abs=1e-6)


def test_decisions_near_end_of_history_are_unsampled_not_shortened():
    snaps, bench = _world()
    res = backtest.evaluate(snaps, bench)
    # 30 dates; f5 needs i+5 in range -> 25 scorable decisions per ticker
    assert res["leans"]["pile_on"]["n"] == 25
    assert res["leans"]["trim"]["n"] == 25


def test_hit_semantics_per_lean():
    snaps, bench = _world()
    res = backtest.evaluate(snaps, bench)
    assert res["leans"]["pile_on"]["hit_rate"] == 100.0   # rose vs flat bench
    assert res["leans"]["trim"]["hit_rate"] == 100.0      # lagged -> trim was right
    assert res["leans"]["pile_on"]["avg_excess20"] > 0
    assert res["dimensions"]["downtrend"]["avg_fwd20"] < 0


def test_one_decision_per_ticker_day():
    snaps, bench = _world()
    d = DATES[0]
    snaps.append(_snap(d, [_tk("AAA", 100.0, "pile_on")]))  # second snapshot same day
    res = backtest.evaluate(snaps, bench)
    assert res["leans"]["pile_on"]["n"] == 25               # still one per day


def test_report_refuses_conclusions_under_min_n():
    snaps, bench = _world()
    report = backtest.render_report(backtest.evaluate(snaps, bench))
    assert "insufficient sample, no conclusion" in report   # n=25 < 30
    assert "predictive" not in report


def test_report_concludes_at_sufficient_n():
    snaps, bench = _world()
    # extend the world to 45 sessions -> n = 40 >= 30
    extra = [date(2026, 3, 2) + timedelta(days=i + (i // 5) * 2) for i in range(15)]
    for j, d in enumerate(extra):
        i = 30 + j
        snaps.append(_snap(d, [_tk("AAA", 100.0 * (1.01 ** i), "pile_on"),
                               _tk("BBB", 100.0 * (0.99 ** i), "trim", dims=["downtrend"])]))
        bench[d] = 100.0
    report = backtest.render_report(backtest.evaluate(snaps, bench))
    assert "predictive at this sample size" in report
    assert "no conclusion" not in report.split("## By deterioration")[0]


# ── performance: TWR, drawdown, benchmarks ────────────────────────────────

def test_contribution_is_not_a_return():
    history = [
        {"as_of_date": "2026-06-01", "book_value": 1000.0, "invested": 1000.0},
        {"as_of_date": "2026-06-02", "book_value": 1100.0, "invested": 1000.0},  # +10%
        # +$1000 of NEW MONEY lands, then the (now 2100) book grows +10%:
        {"as_of_date": "2026-06-03", "book_value": 2310.0, "invested": 2000.0},
    ]
    assert performance.twr_pct(history) == pytest.approx(21.0)  # 1.1 × 1.1 − 1
    # the naive read would be 2310/1000 − 1 = +131% — that's the bug TWR avoids


def test_max_drawdown_on_the_twr_index():
    history = [
        {"as_of_date": "2026-06-01", "book_value": 1000.0, "invested": 1000.0},
        {"as_of_date": "2026-06-02", "book_value": 900.0, "invested": 1000.0},   # −10%
        {"as_of_date": "2026-06-03", "book_value": 1100.0, "invested": 1000.0},
    ]
    assert performance.max_drawdown_pct(history) == pytest.approx(-10.0)


def test_withdrawal_is_not_a_drawdown():
    history = [
        {"as_of_date": "2026-06-01", "book_value": 1000.0, "invested": 1000.0},
        # trimmed half the book (invested down 500): not a loss
        {"as_of_date": "2026-06-02", "book_value": 500.0, "invested": 500.0},
        {"as_of_date": "2026-06-03", "book_value": 505.0, "invested": 500.0},
    ]
    assert performance.max_drawdown_pct(history) == pytest.approx(0.0)


def test_compute_performance_vs_benchmarks():
    history = [
        {"as_of_date": "2026-06-01", "book_value": 1000.0, "invested": 1000.0},
        {"as_of_date": "2026-06-05", "book_value": 1100.0, "invested": 1000.0},
    ]
    spy = {date(2026, 6, 1): 100.0, date(2026, 6, 5): 102.0}
    out = performance.compute_performance(history, spy=spy, qqq=None)
    assert out["twr_pct"] == pytest.approx(10.0)
    assert out["spy_pct"] == pytest.approx(2.0)
    assert out["excess_vs_spy_pp"] == pytest.approx(8.0)
    assert out["qqq_pct"] is None
    assert out["since"] == "2026-06-01"


def test_insufficient_history_is_none():
    assert performance.compute_performance(
        [{"as_of_date": "2026-06-01", "book_value": 1000.0, "invested": 1000.0}]) is None
