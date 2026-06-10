"""Sleeve performance (P10): is this satellite sleeve actually beating the market?

Time-weighted return (TWR) over the stored snapshot history, so CONTRIBUTIONS
DON'T COUNT AS RETURNS: adding $1,000 of new money must not read as a +5% day.

Flows (review remediation R1-1): the pipeline passes EXACT flows from the
transactions ledger — buy cost (shares·price+fees) and sale PROCEEDS
(shares·price−fees) per day. Convention: buy cash is at risk from the start of
its period; sale proceeds were at risk until the sale —
    r_t = (BV_t + sells_t) / (BV_{t-1} + buys_t) − 1
which prices a loss-realizing sale correctly (the old invested-delta
approximation ignored realized P/L and permanently overstated TWR after a
realized loss). When no flows are supplied (tests/offline), the invested-delta
approximation is used and the result is labelled as such — it can misstate by
the realized P/L of sold lots.

Pure math over (date, book_value, invested) rows + benchmark close maps; the
pipeline wires it from Postgres + the already-fetched benchmark history.
"""
from __future__ import annotations

from datetime import date
from typing import Any

Flows = dict[date, dict[str, float]]  # {trade_date: {"buys": $, "sells": $}}


def _d(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def _pair_flow(prev_d: date, cur_d: date, flows: Flows) -> tuple[float, float]:
    """Sum ledger flows landing after prev_d up to and including cur_d."""
    buys = sells = 0.0
    for d, f in flows.items():
        if prev_d < d <= cur_d:
            buys += f.get("buys", 0.0)
            sells += f.get("sells", 0.0)
    return buys, sells


def _chain(history: list[dict[str, Any]], flows: Flows | None) -> list[float]:
    """The TWR index series (starting at 1.0)."""
    rows = [h for h in history if h.get("book_value") and h.get("invested") is not None]
    idx_series = [1.0]
    for prev, cur in zip(rows, rows[1:]):
        bv_prev, bv_cur = float(prev["book_value"]), float(cur["book_value"])
        if flows is not None:
            pd_, cd = _d(prev.get("as_of_date")), _d(cur.get("as_of_date"))
            buys, sells = _pair_flow(pd_, cd, flows) if (pd_ and cd) else (0.0, 0.0)
            base, top = bv_prev + buys, bv_cur + sells
        else:
            # invested-delta approximation (offline fallback): exact for buys,
            # off by realized P/L for sells.
            flow = float(cur["invested"]) - float(prev["invested"])
            base, top = bv_prev + flow, bv_cur
        if base <= 0:
            continue
        idx_series.append(idx_series[-1] * (top / base))
    return idx_series


def twr_pct(history: list[dict[str, Any]], flows: Flows | None = None) -> float | None:
    series = _chain(history, flows)
    if len(series) < 2:
        return None
    return round((series[-1] - 1.0) * 100.0, 2)


def max_drawdown_pct(history: list[dict[str, Any]], flows: Flows | None = None) -> float | None:
    """Max drawdown on the TWR index (raw book value would read a withdrawal as
    a crash). Returned as a negative percentage."""
    series = _chain(history, flows)
    if len(series) < 2:
        return None
    peak, mdd = series[0], 0.0
    for v in series[1:]:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
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
                        qqq: dict[date, float] | None = None,
                        flows: Flows | None = None,
                        realized_pl: float | None = None,
                        unrealized_pl: float | None = None) -> dict[str, Any] | None:
    """The snapshot `performance` block. None when there's not enough history."""
    rows = sorted((h for h in history if h.get("as_of_date")), key=lambda h: str(h["as_of_date"]))
    if len(rows) < 2:
        return None
    twr = twr_pct(rows, flows)
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
        "max_drawdown_pct": max_drawdown_pct(rows, flows),
        "realized_pl": realized_pl,
        "unrealized_pl": unrealized_pl,
        "n_sessions": len({str(r["as_of_date"]) for r in rows}),
        "note": ("time-weighted (contributions excluded); flows from the trade ledger"
                 if flows is not None else
                 "time-weighted (contributions excluded); flows approximated from invested "
                 "deltas — may misstate by realized P/L of sold lots"),
    }
