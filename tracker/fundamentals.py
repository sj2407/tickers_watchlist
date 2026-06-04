"""Quarterly fundamentals: revenue/EPS growth, gross-margin trend, P/E inputs,
and the raw figures the thesis-break flags consume.

Source: FMP (FMP_API_KEY) with a yfinance fallback. Pure-compute is separated
from fetching so the math is unit-testable without the network: `compute()`
accepts already-fetched `income` / `surprises` lists (tests inject synthetic
ones); when omitted it fetches live.

`compute()` is None-safe end to end — a missing key, empty response, or short
history yields a dict with `source=None` and Nones, never an exception. The
signal layer then flags those metrics `insufficient_data`.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .config import get_key

FMP_BASE = "https://financialmodelingprep.com/api/v3"
_session = requests.Session()


# ── fetchers (thin; return parsed lists, newest-quarter-first) ─────────

def _fmp_get(path: str, params: dict[str, Any]) -> Any:
    key = get_key("FMP_API_KEY")
    if not key:
        return None
    params = {**params, "apikey": key}
    for attempt in range(2):
        try:
            r = _session.get(f"{FMP_BASE}{path}", params=params, timeout=15)
            if r.status_code == 429:
                time.sleep(1.0 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 1:
                return None
            time.sleep(0.5)
    return None


def fmp_income(ticker: str, limit: int = 8) -> list[dict] | None:
    data = _fmp_get(f"/income-statement/{ticker}", {"period": "quarter", "limit": limit})
    return data if isinstance(data, list) and data else None


def fmp_surprises(ticker: str) -> list[dict] | None:
    data = _fmp_get(f"/earnings-surprises/{ticker}", {})
    return data if isinstance(data, list) and data else None


def yf_income(ticker: str) -> list[dict] | None:
    """Fallback: shape yfinance quarterly income into FMP-like dicts (newest first)."""
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        q = t.quarterly_income_stmt
        if q is None or q.empty:
            return None
        rows: list[dict] = []
        for col in q.columns:  # columns are period end dates, newest first
            def g(label):
                try:
                    return float(q.loc[label, col])
                except Exception:
                    return None
            rev = g("Total Revenue")
            gp = g("Gross Profit")
            ni = g("Net Income")
            rows.append({
                "date": str(col.date()) if hasattr(col, "date") else str(col),
                "period": None,
                "revenue": rev,
                "grossProfit": gp,
                "eps": None,  # yfinance quarterly EPS is unreliable; leave None
                "netIncome": ni,
            })
        return rows or None
    except Exception:
        return None


# ── pure compute ───────────────────────────────────────────────────────

def _f(v) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1.0) * 100.0, 1)


def _margin(row: dict) -> float | None:
    rev = _f(row.get("revenue"))
    gp = _f(row.get("grossProfit"))
    if rev in (None, 0) or gp is None:
        return None
    return gp / rev * 100.0


def compute(
    ticker: str,
    income: list[dict] | None = None,
    surprises: list[dict] | None = None,
) -> dict[str, Any]:
    """Return a None-safe fundamentals dict. Fetches if inputs not injected."""
    source = None
    if income is None:
        income = fmp_income(ticker)
        if income:
            source = "fmp"
        else:
            income = yf_income(ticker)
            source = "yfinance" if income else None
    else:
        source = "injected"

    out: dict[str, Any] = {
        "source": source, "report_date": None, "fiscal_period": None,
        "revenue": None, "revenue_yoy": None, "revenue_qoq_pct": None,
        "eps": None, "eps_yoy": None, "eps_ttm": None,
        "gross_margin": None, "gross_margin_qoq_pp": None,
        "eps_miss_count_last3": None,
    }
    if not income:
        return out

    q0 = income[0]
    out["report_date"] = q0.get("date")
    out["fiscal_period"] = q0.get("period")
    out["revenue"] = _f(q0.get("revenue"))
    out["eps"] = _f(q0.get("eps"))

    rev0 = _f(q0.get("revenue"))
    if len(income) > 4:
        out["revenue_yoy"] = _pct(rev0, _f(income[4].get("revenue")))
        out["eps_yoy"] = _pct(_f(q0.get("eps")), _f(income[4].get("eps")))
    if len(income) > 1:
        out["revenue_qoq_pct"] = _pct(rev0, _f(income[1].get("revenue")))
        gm0, gm1 = _margin(q0), _margin(income[1])
        if gm0 is not None and gm1 is not None:
            out["gross_margin_qoq_pp"] = round(gm0 - gm1, 2)
    out["gross_margin"] = round(_margin(q0), 2) if _margin(q0) is not None else None

    eps_vals = [_f(r.get("eps")) for r in income[:4]]
    if all(v is not None for v in eps_vals) and eps_vals:
        out["eps_ttm"] = round(sum(eps_vals), 4)

    # repeated EPS misses over the last 3 reported quarters
    if surprises is None and source == "fmp":
        surprises = fmp_surprises(ticker)
    if isinstance(surprises, list) and surprises:
        misses = 0
        for s in surprises[:3]:
            act = _f(s.get("actualEarningResult"))
            est = _f(s.get("estimatedEarning"))
            if act is not None and est is not None and act < est:
                misses += 1
        out["eps_miss_count_last3"] = misses

    return out
