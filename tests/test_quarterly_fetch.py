import pandas as pd

from tracker.quarterly import quarters_from_yf, rev_qoq


def _df(rows: dict, cols: list[str]):
    return pd.DataFrame(rows, index=list(rows.keys()), columns=[pd.Timestamp(c) for c in cols]) if False else pd.DataFrame(
        {pd.Timestamp(c): {k: rows[k][i] for k in rows} for i, c in enumerate(cols)}
    )


def test_parses_newest_first_with_eps_and_margin():
    cols = ["2026-04-30", "2026-01-31", "2025-10-31", "2025-07-31", "2025-04-30"]
    rows = {
        "Total Revenue": [7910e6, 7012e6, 6800e6, 7302e6, 7100e6],
        "Diluted EPS": [3.51, 2.54, 2.38, 2.22, 2.63],
        "Gross Profit": [3947e6, 3435e6, 3265e6, 3562e6, 3485e6],
    }
    qs = quarters_from_yf(_df(rows, cols))
    assert [q.period_end.isoformat() for q in qs] == sorted(cols, reverse=True)
    assert qs[0].revenue == 7910e6 and qs[0].eps == 3.51
    assert rev_qoq(qs) == round((7910 / 7012 - 1) * 100, 2)


def test_missing_eps_row_yields_none_eps():
    cols = ["2026-04-30", "2026-01-31"]
    rows = {"Total Revenue": [100.0, 90.0]}  # no EPS, no Gross Profit
    qs = quarters_from_yf(_df(rows, cols))
    assert qs and qs[0].eps is None and qs[0].gross_profit is None
    assert qs[0].revenue == 100.0


def test_falls_back_to_basic_eps():
    cols = ["2026-04-30", "2026-01-31"]
    rows = {"Total Revenue": [100.0, 90.0], "Basic EPS": [1.2, 1.0]}
    qs = quarters_from_yf(_df(rows, cols))
    assert qs[0].eps == 1.2


def test_nan_cells_become_none():
    cols = ["2026-04-30", "2026-01-31"]
    rows = {"Total Revenue": [float("nan"), 90.0], "Diluted EPS": [1.2, float("nan")]}
    qs = quarters_from_yf(_df(rows, cols))
    assert qs[0].revenue is None and qs[1].eps is None


def test_empty_or_none_frame():
    assert quarters_from_yf(None) == []
    assert quarters_from_yf(pd.DataFrame()) == []
