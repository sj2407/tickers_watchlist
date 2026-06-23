"""Thin data-source clients. Pure fetching, no interpretation.

- yfinance: historical OHLCV (returns + technicals), fast quotes, earnings dates.
- Finnhub:  company news, earnings calendar, analyst recommendation trends.

Finnhub calls degrade gracefully to empty results if the key is missing or the
endpoint is rate-limited, so the pipeline still produces a useful snapshot.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from .config import get_key

FINNHUB_BASE = "https://finnhub.io/api/v1"
_session = requests.Session()

# Per-run Finnhub call counter (lets us prove light intraday runs make ~0 metered calls)
# + failure counter (surfaced in the snapshot's data_health so degraded fetches are
# never indistinguishable from "no news").
_finnhub_calls = 0
_finnhub_failures = 0


def finnhub_call_count() -> int:
    return _finnhub_calls


def finnhub_failure_count() -> int:
    return _finnhub_failures


def reset_finnhub_calls() -> None:
    global _finnhub_calls, _finnhub_failures
    _finnhub_calls = 0
    _finnhub_failures = 0


# --------------------------------------------------------------------------- #
# yfinance
# --------------------------------------------------------------------------- #
# Overnight / global markets that move the US open: Asia + Europe trade while the
# US sleeps and are LIVE at the 9am ET pre-open run; index futures point at the open.
# All "up = good" so the UI can color them uniformly. yfinance fast_info is empty for
# these symbols, so recent_change() reads them off a short daily history instead.
GLOBAL_MARKETS_DEFAULT: list[dict[str, str]] = [
    {"symbol": "^N225", "label": "Nikkei 225", "region": "Asia"},
    {"symbol": "^KS11", "label": "KOSPI", "region": "Asia"},
    {"symbol": "^HSI", "label": "Hang Seng", "region": "Asia"},
    {"symbol": "^TWII", "label": "Taiwan", "region": "Asia"},
    {"symbol": "^STOXX50E", "label": "Euro Stoxx 50", "region": "Europe"},
    {"symbol": "^GDAXI", "label": "DAX", "region": "Europe"},
    {"symbol": "^FTSE", "label": "FTSE 100", "region": "Europe"},
    {"symbol": "ES=F", "label": "S&P 500 fut", "region": "US futures"},
    {"symbol": "NQ=F", "label": "Nasdaq 100 fut", "region": "US futures"},
]


def recent_change(symbol: str) -> dict[str, Any] | None:
    """Last close + prior close from a short daily history. Works for indices and
    futures (where fast_info is empty). None on failure/empty — caller drops it, so
    a degraded global-markets fetch never blocks a run."""
    try:
        df = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
    except Exception:
        return None
    if df is None or df.empty or "Close" not in df.columns:
        return None
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return None
    return {
        "last": round(float(closes.iloc[-1]), 2),
        "prev_close": round(float(closes.iloc[-2]), 2),
        "as_of_date": pd.Timestamp(closes.index[-1]).date().isoformat(),
    }


def price_history(ticker: str, days: int = 400) -> pd.DataFrame:
    """Daily OHLCV indexed by date (tz-naive). Empty frame on failure."""
    try:
        df = yf.Ticker(ticker).history(period=f"{days}d", interval="1d", auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.title)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if "Adj Close" in df.columns:
        # Dividend-adjusted closes (total return) — used ONLY by returns/relative
        # strength; technicals, charts and position math stay on raw Close.
        cols.append("Adj Close")
    return df[cols]


def fast_quote(ticker: str) -> dict[str, Any]:
    """Latest price + pre/post market if available, via yfinance fast_info/info."""
    out: dict[str, Any] = {}
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        out["last_price"] = _f(fi.get("last_price"))
        out["prev_close"] = _f(fi.get("previous_close"))
        out["open"] = _f(fi.get("open"))
        out["day_high"] = _f(fi.get("day_high"))
        out["day_low"] = _f(fi.get("day_low"))
        out["year_high"] = _f(fi.get("year_high"))
        out["year_low"] = _f(fi.get("year_low"))
    except Exception:
        pass
    return out


def earnings_dates_yf(ticker: str) -> list[date]:
    """Upcoming + recent earnings dates from yfinance (sorted ascending)."""
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=12)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    return sorted({pd.Timestamp(ts).date() for ts in df.index})


# --------------------------------------------------------------------------- #
# Finnhub
# --------------------------------------------------------------------------- #
def _finnhub_get(path: str, params: dict[str, Any]) -> Any:
    global _finnhub_calls, _finnhub_failures
    key = get_key("FINNHUB_API_KEY")
    if not key:
        return None
    _finnhub_calls += 1  # count metered Finnhub calls actually attempted
    params = {**params, "token": key}
    for attempt in range(3):
        try:
            r = _session.get(f"{FINNHUB_BASE}{path}", params=params, timeout=15)
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 2:
                _finnhub_failures += 1
                return None
            time.sleep(1.0)
    _finnhub_failures += 1  # rate-limited through all retries
    return None


def company_news(ticker: str, lookback_days: int = 4, limit: int = 8) -> list[dict[str, Any]]:
    today = date.today()
    frm = today - timedelta(days=lookback_days)
    data = _finnhub_get(
        "/company-news",
        {"symbol": ticker, "from": frm.isoformat(), "to": today.isoformat()},
    )
    if not isinstance(data, list):
        return []
    items = []
    for n in data[:limit]:
        items.append(
            {
                "datetime": _iso_from_epoch(n.get("datetime")),
                "headline": n.get("headline"),
                "source": n.get("source"),
                "url": n.get("url"),
                "summary": n.get("summary"),
                "category": n.get("category"),
            }
        )
    return items


def recommendation_trend(ticker: str) -> dict[str, Any] | None:
    data = _finnhub_get("/stock/recommendation", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return None
    latest = data[0]  # most recent period first
    return {
        "period": latest.get("period"),
        "strongBuy": latest.get("strongBuy"),
        "buy": latest.get("buy"),
        "hold": latest.get("hold"),
        "sell": latest.get("sell"),
        "strongSell": latest.get("strongSell"),
    }


def earnings_calendar(ticker: str, ahead_days: int = 120) -> list[dict[str, Any]] | None:
    """None = transport failure (DON'T cache — retry next call); [] = Finnhub
    answered and genuinely has no events in the window (cacheable for the day)."""
    today = date.today()
    data = _finnhub_get(
        "/calendar/earnings",
        {
            "symbol": ticker,
            "from": (today - timedelta(days=120)).isoformat(),
            "to": (today + timedelta(days=ahead_days)).isoformat(),
        },
    )
    if not isinstance(data, dict):
        return None  # failed/rate-limited/no key — never "no earnings"
    rows = data.get("earningsCalendar") or []
    out = []
    for r in rows:
        out.append(
            {
                "date": r.get("date"),
                "hour": r.get("hour"),  # bmo / amc / dmh
                "eps_estimate": r.get("epsEstimate"),
                "eps_actual": r.get("epsActual"),
                "revenue_estimate": r.get("revenueEstimate"),
                "revenue_actual": r.get("revenueActual"),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _iso_from_epoch(ts: Any) -> str | None:
    try:
        return pd.Timestamp(int(ts), unit="s", tz="UTC").isoformat()
    except (TypeError, ValueError):
        return None
