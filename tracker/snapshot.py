"""Build the snapshot JSON the routine + web app consume.

This orchestrates the dumb layer only. It leaves placeholder fields
(`catalyst_summary`, `earnings_recap`, `final_lean`, `rationale`) empty — the
Claude routine fills those in during its run, on the subscription.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from . import market_data as md
from . import sources, signals, store
from .calendar_utils import session_phase
from .config import load_config, load_env


def _price_series(hist: pd.DataFrame, sessions: int = 180) -> list[dict[str, Any]]:
    """Compact OHLC tail for charting: [{t, o, h, l, c, v}, ...] (date ascending)."""
    if hist.empty:
        return []
    tail = hist.tail(sessions)
    out = []
    for ts, row in tail.iterrows():
        out.append(
            {
                "t": ts.date().isoformat(),
                "o": round(float(row["Open"]), 2),
                "h": round(float(row["High"]), 2),
                "l": round(float(row["Low"]), 2),
                "c": round(float(row["Close"]), 2),
                "v": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
            }
        )
    return out


def _days_until(target: date | None, ref: date) -> int | None:
    if target is None:
        return None
    return (target - ref).days


def _next_earnings(ticker: str, today: date) -> dict[str, Any]:
    """Merge Finnhub calendar + yfinance dates → next upcoming + last reported."""
    out: dict[str, Any] = {}
    cal = sources.earnings_calendar(ticker)
    yf_dates = sources.earnings_dates_yf(ticker)

    cal_dates = []
    for row in cal:
        try:
            cal_dates.append((date.fromisoformat(row["date"]), row))
        except (TypeError, ValueError):
            continue

    all_dates = sorted({d for d, _ in cal_dates} | set(yf_dates))
    upcoming = [d for d in all_dates if d >= today]
    past = [d for d in all_dates if d < today]

    if upcoming:
        nxt = upcoming[0]
        out["next_date"] = nxt.isoformat()
        out["days_until_next"] = _days_until(nxt, today)
        for d, row in cal_dates:
            if d == nxt:
                out["next_hour"] = row.get("hour")
                out["next_eps_estimate"] = row.get("eps_estimate")
                out["next_revenue_estimate"] = row.get("revenue_estimate")
    if past:
        last = past[-1]
        out["last_date"] = last.isoformat()
        for d, row in cal_dates:
            if d == last:
                out["last_eps_estimate"] = row.get("eps_estimate")
                out["last_eps_actual"] = row.get("eps_actual")
                out["last_revenue_estimate"] = row.get("revenue_estimate")
                out["last_revenue_actual"] = row.get("revenue_actual")
    # surprise flags for the most recent reported quarter (numbers only; narrative is the routine's job)
    ea, ee = out.get("last_eps_actual"), out.get("last_eps_estimate")
    if ea is not None and ee not in (None, 0):
        out["last_eps_surprise_pct"] = round((ea - ee) / abs(ee) * 100, 1)
    return out


def build_snapshot(mode: str) -> dict[str, Any]:
    load_env()
    cfg = load_config()
    tz = cfg["timezone"]
    today = datetime.now(ZoneInfo(tz)).date()
    tickers = store.get_tickers()       # DB watchlist, or config.yaml in file mode
    holdings = store.get_holdings()     # DB current_positions, or holdings.json

    # benchmarks (fetched once)
    bench_hist = sources.price_history(cfg["benchmark"], cfg["history_days"])

    rows: list[dict[str, Any]] = []
    book_value = 0.0
    # first pass for book value (needs last prices)
    last_prices: dict[str, float | None] = {}
    hists: dict[str, pd.DataFrame] = {}
    quotes: dict[str, dict] = {}
    for tk in tickers:
        h = sources.price_history(tk, cfg["history_days"])
        hists[tk] = h
        q = sources.fast_quote(tk)
        quotes[tk] = q
        last = q.get("last_price")
        if last is None and not h.empty:
            last = round(float(h["Close"].dropna().iloc[-1]), 2)
        last_prices[tk] = last
        hold = holdings.get(tk)
        if hold and last:
            book_value += float(hold.get("shares") or 0) * last

    for tk in tickers:
        h = hists[tk]
        q = quotes[tk]
        last = last_prices[tk]

        # Fill price gaps from history when the live quote is sparse.
        closes = h["Close"].dropna() if not h.empty else None
        prev_close = q.get("prev_close")
        if prev_close is None and closes is not None and len(closes) >= 2:
            # second-to-last close is the prior session's close
            prev_close = round(float(closes.iloc[-2]), 2)
        if q.get("day_high") is None and not h.empty:
            q["day_high"] = round(float(h["High"].dropna().iloc[-1]), 2)
            q["day_low"] = round(float(h["Low"].dropna().iloc[-1]), 2)
        q["prev_close"] = prev_close

        tech = md.compute_technicals(h)
        rs = md.relative_strength(h, bench_hist)
        rets = md.compute_returns(h)
        series = _price_series(h, sessions=180)
        fund = store.get_fundamentals(tk)
        # P/E from live price + trailing-4Q EPS (computed here so it stays time-stamped)
        ettm = fund.get("eps_ttm")
        fund["pe"] = round(last / ettm, 1) if (last and ettm and ettm > 0) else None
        pos = md.position_math(holdings.get(tk), last, book_value or None)
        earn = _next_earnings(tk, today)

        row: dict[str, Any] = {
            "ticker": tk,
            "price": {
                "last": last,
                "prev_close": q.get("prev_close"),
                "open": q.get("open"),
                "day_high": q.get("day_high"),
                "day_low": q.get("day_low"),
                "day_change_pct": md._pct(last, q.get("prev_close")),
            },
            "returns": rets,
            "relative_strength": rs,
            "technicals": tech,
            "fundamentals": fund,
            "series": series,
            "position": pos,
            "earnings": earn,
            "analyst": sources.recommendation_trend(tk),
            "news": sources.company_news(
                tk, cfg["news_lookback_days"], cfg["max_news_per_ticker"]
            ),
            # filled by the Claude routine (subscription), left empty by the pipeline:
            "takeaway": None,        # one plain-English line: what's going on + what to consider
            "sentiment": None,       # bullish | bearish | neutral | mixed
            "catalyst_summary": None,
            "earnings_recap": None,
            "final_lean": None,
            "rationale": None,
        }
        row["signals"] = signals.build_signals(row, cfg)
        rows.append(row)

    portfolio = _portfolio_block(rows, book_value)
    return {
        "generated_at": datetime.now(ZoneInfo(tz)).isoformat(),
        "mode": mode,  # "preopen" | "postclose"
        "session_phase": session_phase(tz),
        "as_of_date": today.isoformat(),
        "benchmark": cfg["benchmark"],
        "min_position_usd": cfg["min_position_usd"],
        "portfolio": portfolio,
        "tickers": rows,
        # filled by the Claude routine:
        "market_recap": None,
        "macro_context": None,
        "alerts": _mechanical_alerts(rows, cfg),
    }


def _portfolio_block(rows: list[dict[str, Any]], book_value: float) -> dict[str, Any]:
    held = [r for r in rows if r["position"].get("held")]
    total_pl = sum((r["position"].get("unrealized_pl") or 0) for r in held)
    invested = sum((r["position"].get("invested") or 0) for r in held)
    movers = [
        (r["ticker"], r["price"].get("day_change_pct"))
        for r in rows
        if r["price"].get("day_change_pct") is not None
    ]
    movers.sort(key=lambda x: x[1])
    return {
        "book_value": round(book_value, 2),
        "invested": round(invested, 2),
        "unrealized_pl": round(total_pl, 2),
        "unrealized_pl_pct": round(total_pl / invested * 100, 2) if invested else None,
        "positions_count": len(held),
        "top_gainer": movers[-1] if movers else None,
        "top_loser": movers[0] if movers else None,
    }


def _mechanical_alerts(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Time-sensitive flags worth a push. Narrative alerts are added by the routine."""
    alerts = []
    for r in rows:
        tk = r["ticker"]
        days = r["earnings"].get("days_until_next")
        if days == 7:
            alerts.append({"ticker": tk, "type": "earnings_t7", "msg": f"{tk} reports in ~1 week ({r['earnings'].get('next_date')})"})
        if days == 1:
            alerts.append({"ticker": tk, "type": "earnings_t1", "msg": f"{tk} reports tomorrow ({r['earnings'].get('next_hour') or 'time TBD'})"})
        chg = r["price"].get("day_change_pct")
        if chg is not None and abs(chg) >= 7:
            alerts.append({"ticker": tk, "type": "big_move", "msg": f"{tk} moved {chg:+.1f}% today"})
        # NOTE: no position-weight alert — this is a small satellite sleeve; size isn't a risk here.
    return alerts
