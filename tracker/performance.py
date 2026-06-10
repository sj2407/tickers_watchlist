"""Sleeve performance (P10): is this satellite sleeve actually beating the market?

Time-weighted return (TWR) over the stored snapshot history, so CONTRIBUTIONS
DON'T COUNT AS RETURNS: adding $1,000 of new money must not read as a +5% day.
Flows are approximated by the change in invested capital between consecutive
snapshots (the ledger's cost basis) — exact for buys, approximate for sells (off
by the realized P/L of the sold lot); documented, conservative, and consistent.

Pure math over (date, book_value, invested) rows + benchmark close maps; the
pipeline wires it from Postgres + the already-fetched benchmark history.
"""
from __future__ import annotations

from datetime import date
from typing import Any


def twr_pct(history: list[dict[str, Any]]) -> float | None:
    """Chain daily returns with the invested-delta flow adjustment, flows assumed
    at the START of each period (simple-Dietz style):
    r_t = BV_t / (BV_{t-1} + flow_t) − 1, flow_t = invested_t − invested_{t-1}."""
    rows = [h for h in history if h.get("book_value") and h.get("invested") is not None]
    if len(rows) < 2:
        return None
    idx = 1.0
    for prev, cur in zip(rows, rows[1:]):
        flow = float(cur["invested"]) - float(prev["invested"])
        base = float(prev["book_value"]) + flow
        if base <= 0:
            continue
        idx *= float(cur["book_value"]) / base
    return round((idx - 1.0) * 100.0, 2)


def max_drawdown_pct(history: list[dict[str, Any]]) -> float | None:
    """Max drawdown on the TWR index (raw book value would read a withdrawal as
    a crash). Returned as a negative percentage."""
    rows = [h for h in history if h.get("book_value") and h.get("invested") is not None]
    if len(rows) < 2:
        return None
    idx, peak, mdd = 1.0, 1.0, 0.0
    for prev, cur in zip(rows, rows[1:]):
        flow = float(cur["invested"]) - float(prev["invested"])
        base = float(prev["book_value"]) + flow
        if base <= 0:
            continue
        idx *= float(cur["book_value"]) / base
        peak = max(peak, idx)
        mdd = min(mdd, idx / peak - 1.0)
    return round(mdd * 100.0, 2)


def bench_return_pct(closes: dict[date, float] | None, start: date, end: date) -> float | None:
    """Benchmark total return between the closest available sessions to [start, end]."""
    if not closes:
        return None
    dates = sorted(closes)
    s = next((d for d in dates if d >= start), None)
    e = next((d for d in reversed(dates) if d <= end), None)
    if s is None or e is None or s >= e or closes[s] == 0:
        return None
    return round((closes[e] / closes[s] - 1.0) * 100.0, 2)


def compute_performance(history: list[dict[str, Any]],
                        spy: dict[date, float] | None = None,
                        qqq: dict[date, float] | None = None) -> dict[str, Any] | None:
    """The snapshot `performance` block. None when there's not enough history."""
    rows = sorted((h for h in history if h.get("as_of_date")), key=lambda h: str(h["as_of_date"]))
    if len(rows) < 2:
        return None
    twr = twr_pct(rows)
    if twr is None:
        return None
    start = date.fromisoformat(str(rows[0]["as_of_date"])[:10])
    end = date.fromisoformat(str(rows[-1]["as_of_date"])[:10])
    spy_ret = bench_return_pct(spy, start, end)
    qqq_ret = bench_return_pct(qqq, start, end)
    return {
        "since": start.isoformat(),
        "twr_pct": twr,
        "spy_pct": spy_ret,
        "qqq_pct": qqq_ret,
        "excess_vs_spy_pp": round(twr - spy_ret, 2) if spy_ret is not None else None,
        "max_drawdown_pct": max_drawdown_pct(rows),
        "n_sessions": len({str(r["as_of_date"]) for r in rows}),
        "note": "time-weighted (contributions excluded); sell flows approximated by invested deltas",
    }
