"""Seed the watchlist + opening transactions from real prices (idempotent).

    python -m tracker.seed

- 18 names: entered TODAY at $200 each  -> buy shares = 200 / today's close.
- NOW (ServiceNow): 8.63537 shares entered ~1 week ago -> buy at the close ~1 week ago.

Only inserts an opening trade if a ticker has none yet, so re-running is safe.
Prices come from the live data source — never hardcoded.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from .config import load_env
from . import db, sources

TODAY_200 = [
    "IONQ", "MU", "SNDK", "CRDO", "CEVA", "CRWD", "TSM", "LLY", "ASML",
    "MP", "CRWV", "AVGO", "OUST", "NVDA", "AMAT", "LRCX", "MRVL", "KLAC",
]
# special: (ticker, shares, entered_days_ago)
SPECIAL = ("NOW", 8.63537, 7)

# Existing holdings given as (ticker, shares) with no known entry date/price.
# Seeded at today's price (cost basis = today → since-entry starts ~0); the user
# can record the real entry later to make since-entry accurate.
HELD_SHARES = [
    ("COHR", 1.85723),
    ("LITE", 0.63823),
]


def _last_close(hist: pd.DataFrame) -> float | None:
    if hist.empty:
        return None
    return round(float(hist["Close"].dropna().iloc[-1]), 2)


def _close_n_days_ago(hist: pd.DataFrame, days: int) -> tuple[float | None, datetime | None]:
    if hist.empty:
        return None, None
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    closes = hist["Close"].dropna()
    on_or_before = closes[closes.index.date <= cutoff]
    if on_or_before.empty:
        ts = closes.index[0]
        return round(float(closes.iloc[0]), 2), ts.to_pydatetime()
    ts = on_or_before.index[-1]
    return round(float(on_or_before.iloc[-1]), 2), ts.to_pydatetime()


def run() -> None:
    load_env()
    if not db.using_db():
        raise SystemExit("DATABASE_URL not set — seed targets Postgres.")

    now = datetime.now(timezone.utc)
    seeded, skipped = 0, 0

    for tk in TODAY_200:
        db.upsert_watchlist(tk)
        if db.transaction_count(tk) > 0:
            skipped += 1
            continue
        hist = sources.price_history(tk, 30)
        price = _last_close(hist)
        if not price:
            print(f"  ! {tk}: no price, watchlist only")
            continue
        shares = round(200.0 / price, 6)
        db.add_transaction(tk, "buy", shares, price, executed_at=now, source="seed",
                           note="opening $200 (today)")
        print(f"  + {tk}: {shares} sh @ ${price} (=$200)")
        seeded += 1

    for tk, shares in HELD_SHARES:
        db.upsert_watchlist(tk)
        if db.transaction_count(tk) > 0:
            skipped += 1
            continue
        hist = sources.price_history(tk, 30)
        price = _last_close(hist)
        if not price:
            print(f"  ! {tk}: no price, watchlist only")
            continue
        db.add_transaction(tk, "buy", round(shares, 6), price, executed_at=now, source="seed",
                           note="existing holding (cost basis = today; entry unknown)")
        print(f"  + {tk}: {shares} sh @ ${price} (=${round(shares*price)})")
        seeded += 1

    tk, shares, days_ago = SPECIAL
    db.upsert_watchlist(tk)
    if db.transaction_count(tk) == 0:
        hist = sources.price_history(tk, 30)
        price, ts = _close_n_days_ago(hist, days_ago)
        if price:
            db.add_transaction(tk, "buy", shares, price, executed_at=ts, source="seed",
                               note=f"opening position (~{days_ago}d ago)")
            print(f"  + {tk}: {shares} sh @ ${price} on {ts.date()} (~${round(shares*price)})")
            seeded += 1
    else:
        skipped += 1

    print(f"seed: {seeded} opened, {skipped} already had trades")


if __name__ == "__main__":
    run()
