"""Per-ET-trading-day cache for slow Finnhub data — earnings calendar + analyst recs ONLY.

Freshness is keyed to an explicit ET calendar date stored on the row (not derived from
fetched_at at read time): a value is fresh iff it was stored on today's ET date. So the
first run of a day refetches; later same-day runs reuse it. Fundamentals are NOT cached
here (the `fundamentals` table is their sole owner).

No DB (file mode) → no caching, just passthrough fetch.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from . import db

ET = ZoneInfo("America/New_York")


def current_et_date(now: datetime | None = None) -> date:
    """Today's date in US/Eastern (the cache's day boundary)."""
    dt = now.astimezone(ET) if now else datetime.now(ET)
    return dt.date()


def is_fresh(trading_day: date | None, now: datetime | None = None) -> bool:
    """Pure freshness check: fresh iff stored on today's ET date."""
    return trading_day is not None and trading_day == current_et_date(now)


def _get(key: str, now: datetime | None = None) -> Any | None:
    if not db.using_db():
        return None
    with db.connect() as c:
        row = c.execute(
            "SELECT payload, trading_day FROM api_cache WHERE cache_key = %s", (key,)
        ).fetchone()
    if row and is_fresh(row["trading_day"], now):
        return row["payload"]
    return None


def _put(key: str, payload: Any, now: datetime | None = None) -> None:
    if not db.using_db():
        return
    today = current_et_date(now)
    with db.connect() as c:
        c.execute(
            "INSERT INTO api_cache (cache_key, payload, trading_day, fetched_at) "
            "VALUES (%s, %s, %s, now()) "
            "ON CONFLICT (cache_key) DO UPDATE SET "
            "payload = EXCLUDED.payload, trading_day = EXCLUDED.trading_day, fetched_at = now()",
            (key, json.dumps(payload, default=str), today),
        )


def cached(key: str, fetch_fn: Callable[[], Any], *, bypass: bool = False,
           now: datetime | None = None) -> Any:
    """Return cached payload if fresh (and not bypassed), else fetch + store.
    `bypass=True` forces a fresh fetch (used by full runs for today's earnings reporters)."""
    if not bypass:
        hit = _get(key, now)
        if hit is not None:
            return hit
    val = fetch_fn()
    if val is not None:
        _put(key, val, now)
    return val
