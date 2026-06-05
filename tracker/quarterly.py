"""Pure quarterly-fundamentals math, no network.

Given a list of quarters (newest first), compute the sequential/annual metrics the
cache can't provide: Rev QoQ, gross margin + margin QoQ, and a *guarded* YoY that
refuses to emit a meaningless percentage (negative/near-zero year-ago denominator).
Everything is None-safe and never returns a misleading number — missing/ambiguous
inputs yield None ("insufficient"), never a false value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Quarter:
    period_end: date
    revenue: float | None = None
    eps: float | None = None
    gross_profit: float | None = None


def finite(x) -> float | None:
    """Coerce to a finite float, else None (scrubs NaN/Inf from feeds)."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)) and math.isfinite(x):
        return float(x)
    return None


def _sorted_newest_first(quarters: list[Quarter]) -> list[Quarter]:
    return sorted(quarters, key=lambda q: q.period_end, reverse=True)


def rev_qoq(quarters: list[Quarter]) -> float | None:
    """Latest quarter's revenue vs the prior quarter, in percent. None if <2 quarters."""
    qs = _sorted_newest_first(quarters)
    if len(qs) < 2:
        return None
    cur, prev = finite(qs[0].revenue), finite(qs[1].revenue)
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur / prev - 1) * 100, 2)


def gross_margin(quarters: list[Quarter]) -> float | None:
    """Latest quarter's gross margin in PERCENT (gross_profit / revenue * 100)."""
    qs = _sorted_newest_first(quarters)
    if not qs:
        return None
    rev, gp = finite(qs[0].revenue), finite(qs[0].gross_profit)
    if rev is None or rev == 0 or gp is None:
        return None
    return round(gp / rev * 100, 2)


def gross_margin_qoq_pp(quarters: list[Quarter]) -> float | None:
    """Change in gross margin vs the prior quarter, in percentage POINTS. None if <2."""
    qs = _sorted_newest_first(quarters)
    if len(qs) < 2:
        return None

    def gm(q: Quarter) -> float | None:
        rev, gp = finite(q.revenue), finite(q.gross_profit)
        if rev is None or rev == 0 or gp is None:
            return None
        return gp / rev * 100

    g0, g1 = gm(qs[0]), gm(qs[1])
    if g0 is None or g1 is None:
        return None
    return round(g0 - g1, 2)


def quarters_from_yf(df) -> list[Quarter]:
    """Parse a yfinance quarterly_income_stmt DataFrame into Quarters (newest first).
    Pure (no network): rows by label, NaN/missing -> None, columns are period-end dates.
    Returns [] if the frame is empty or unusable."""
    if df is None or getattr(df, "empty", True):
        return []
    idx = list(df.index)

    def row(name):
        return df.loc[name] if name in idx else None

    rev = row("Total Revenue")
    eps = row("Diluted EPS")
    if eps is None:
        eps = row("Basic EPS")  # diluted is preferred; fall back to basic
    gp = row("Gross Profit")
    out: list[Quarter] = []
    for col in df.columns:
        pe = col.date() if hasattr(col, "date") else None
        if pe is None:
            continue
        out.append(
            Quarter(
                period_end=pe,
                revenue=finite(rev[col]) if rev is not None else None,
                eps=finite(eps[col]) if eps is not None else None,
                gross_profit=finite(gp[col]) if gp is not None else None,
            )
        )
    return _sorted_newest_first(out)


def record_from_quarters(quarters: list[Quarter]) -> dict | None:
    """Build the fundamentals-table record (the quarterly-derived fields) from quarters.
    None if there are no usable quarters."""
    qs = _sorted_newest_first(quarters)
    if not qs:
        return None
    return {
        "report_date": qs[0].period_end,
        "revenue": finite(qs[0].revenue),
        "eps": finite(qs[0].eps),
        "gross_margin": gross_margin(qs),
        "revenue_qoq_pct": rev_qoq(qs),
        "gross_margin_qoq_pp": gross_margin_qoq_pp(qs),
        "revenue_yoy": yoy_guarded(qs, "revenue"),
        "eps_yoy": yoy_guarded(qs, "eps"),
    }


# A company announces a quarter ~40 days after its period end; the NEXT quarter is
# announced ~130 days after this one's period end. So if the latest earnings date is
# more than this many days past our stored period end, a newer quarter has been
# reported than we hold -> our data is stale.
QUARTER_GAP_MAX_DAYS = 100


def is_stale(report_date, fetched_at, last_date, now, max_age_days: int = 7) -> bool:
    """Decide if our stored quarterly fundamentals are stale, comparing LIKE TO LIKE.
    - no data -> stale
    - the latest earnings announcement is a full cycle past our period end (a newer
      quarter was reported than we hold) -> stale
    - older than the time backstop (restatements / quiet names) -> stale
    `report_date`/`last_date` are dates; `fetched_at`/`now` are datetimes.
    """
    if report_date is None or fetched_at is None:
        return True
    if last_date is not None and (last_date - report_date).days > QUARTER_GAP_MAX_DAYS:
        return True
    if (now - fetched_at).days > max_age_days:
        return True
    return False


def fetch_quarters(ticker: str) -> list[Quarter]:
    """Fetch quarterly income-statement quarters from yfinance (free). [] on any error."""
    try:
        import yfinance as yf

        df = yf.Ticker(ticker).quarterly_income_stmt
    except Exception:
        return []
    return quarters_from_yf(df)


def yoy_guarded(quarters: list[Quarter], field: str) -> float | None:
    """Single-quarter YoY (Q0 vs the same quarter a year ago, Q4) in percent.

    Needs >=5 quarters. Returns None whenever the year-ago denominator is
    non-positive or near-zero (a ratio there is meaningless and could read as a
    spurious sign), so EPS that swung *from* a loss never shows a false negative.
    `field` is "revenue" or "eps".
    """
    qs = _sorted_newest_first(quarters)
    if len(qs) < 5:
        return None
    cur = finite(getattr(qs[0], field))
    prior = finite(getattr(qs[4], field))
    if cur is None or prior is None:
        return None
    floor = 0.02 if field == "eps" else 1.0
    if prior <= 0 or abs(prior) < floor:
        return None
    return round((cur / prior - 1) * 100, 2)
