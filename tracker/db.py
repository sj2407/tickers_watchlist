"""Postgres access for the pipeline (psycopg). Only used when DATABASE_URL is set.

Standard SQL against any Postgres (local container / Neon / Supabase). The app
(TypeScript) talks to the same schema — see web/src/lib/db.ts.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row


def database_url() -> str | None:
    # Local dev uses DATABASE_URL (Docker); Vercel's Neon integration injects
    # WATCHLIST_DATABASE_URL (custom prefix). Accept either.
    return os.environ.get("DATABASE_URL") or os.environ.get("WATCHLIST_DATABASE_URL")


def using_db() -> bool:
    return bool(database_url())


@contextmanager
def connect():
    conn = psycopg.connect(database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_watchlist(active_only: bool = True) -> list[dict[str, Any]]:
    q = "SELECT ticker, active, sector_etf, target, stop, notes FROM watchlist"
    if active_only:
        q += " WHERE active = true"
    q += " ORDER BY ticker"
    with connect() as c:
        return c.execute(q).fetchall()


def fetch_positions() -> dict[str, dict[str, Any]]:
    """Return {ticker: {shares, cost_basis, invested, realized_pl, notes, target, stop}}.

    Shape matches the JSON holdings store so downstream position math is unchanged.
    """
    q = """
      SELECT w.ticker,
             COALESCE(p.shares, 0)  AS shares,
             p.avg_cost             AS cost_basis,
             p.invested,
             p.realized_pl,
             w.notes, w.target, w.stop
      FROM watchlist w
      LEFT JOIN current_positions p ON p.ticker = w.ticker
      WHERE w.active = true
    """
    with connect() as c:
        rows = c.execute(q).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if (r["shares"] or 0) > 0:
            out[r["ticker"]] = {
                "shares": float(r["shares"]),
                "cost_basis": float(r["cost_basis"]) if r["cost_basis"] is not None else None,
                "invested": float(r["invested"]) if r["invested"] is not None else None,
                "realized_pl": float(r["realized_pl"]) if r["realized_pl"] is not None else None,
                "notes": r["notes"] or "",
                "target": r["target"],
                "stop": r["stop"],
            }
    return out


def insert_snapshot(payload: dict[str, Any], mode: str, as_of: date, generated_at: datetime) -> int:
    with connect() as c:
        row = c.execute(
            """
            INSERT INTO snapshots (generated_at, mode, as_of_date, payload)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (generated_at, mode, as_of, json.dumps(payload, default=str)),
        ).fetchone()
    return row["id"]


def get_latest_enriched() -> dict[str, Any] | None:
    """Latest snapshot that has narrative (market_recap set by the routine) — the source
    for carry-forward and what the app should show."""
    with connect() as c:
        row = c.execute(
            "SELECT payload FROM snapshots WHERE payload->>'market_recap' IS NOT NULL "
            "ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
    return row["payload"] if row else None


def update_snapshot(snapshot_id: int, payload: dict[str, Any]) -> bool:
    """Update a SPECIFIC snapshot row (no cross-run clobber)."""
    with connect() as c:
        n = c.execute("UPDATE snapshots SET payload = %s WHERE id = %s",
                      (json.dumps(payload, default=str), snapshot_id)).rowcount
    return n > 0


def update_latest_snapshot(payload: dict[str, Any]) -> bool:
    """Replace the payload of the most recent snapshot (used after enrichment)."""
    with connect() as c:
        row = c.execute("SELECT id FROM snapshots ORDER BY generated_at DESC LIMIT 1").fetchone()
        if not row:
            return False
        c.execute("UPDATE snapshots SET payload = %s WHERE id = %s",
                  (json.dumps(payload, default=str), row["id"]))
    return True


def add_transaction(
    ticker: str, side: str, shares: float, price: float, *, fees: float = 0.0,
    executed_at: datetime | None = None, source: str = "app", note: str = "",
) -> None:
    with connect() as c:
        c.execute(
            """
            INSERT INTO transactions (ticker, side, shares, price, fees, executed_at, source, note)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, now()), %s, %s)
            """,
            (ticker.upper(), side, shares, price, fees, executed_at, source, note),
        )


def upsert_watchlist(ticker: str, **meta: Any) -> None:
    cols = {"sector_etf", "target", "stop", "notes", "active"}
    fields = {k: v for k, v in meta.items() if k in cols}
    set_clause = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
    keys = ["ticker", *fields.keys()]
    placeholders = ", ".join(["%s"] * len(keys))
    with connect() as c:
        c.execute(
            f"INSERT INTO watchlist ({', '.join(keys)}) VALUES ({placeholders}) "
            f"ON CONFLICT (ticker) DO UPDATE SET {set_clause}" if set_clause
            else f"INSERT INTO watchlist (ticker) VALUES (%s) ON CONFLICT (ticker) DO NOTHING",
            [ticker.upper(), *fields.values()] if set_clause else [ticker.upper()],
        )


_FUND_COLS = (
    "report_date", "fiscal_period", "revenue", "revenue_yoy", "revenue_qoq_pct",
    "eps", "eps_yoy", "eps_ttm", "gross_margin", "gross_margin_qoq_pp",
    "eps_miss_count_last3", "source",
)


def fetch_fundamentals(ticker: str) -> dict[str, Any] | None:
    with connect() as c:
        return c.execute(
            "SELECT *, fetched_at FROM fundamentals WHERE ticker = %s", (ticker.upper(),)
        ).fetchone()


def upsert_fundamentals(ticker: str, d: dict[str, Any]) -> None:
    cols = ["ticker", *_FUND_COLS, "fetched_at"]
    placeholders = ", ".join(["%s"] * (len(_FUND_COLS) + 1)) + ", now()"
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in (*_FUND_COLS, "fetched_at"))
    vals = [ticker.upper(), *[d.get(k) for k in _FUND_COLS]]
    with connect() as c:
        c.execute(
            f"INSERT INTO fundamentals ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT (ticker) DO UPDATE SET {updates}",
            vals,
        )


def claim_alert(ticker: str, trigger: str, alert_date) -> bool:
    """Dedup: claim (ticker, trigger) for the given ET date. Returns True only on the
    FIRST claim that day (idempotent via the PK + ON CONFLICT DO NOTHING)."""
    with connect() as c:
        n = c.execute(
            "INSERT INTO intraday_alerts (ticker, trigger, alert_date) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (ticker.upper(), trigger, alert_date),
        ).rowcount
    return n > 0


def transaction_count(ticker: str) -> int:
    with connect() as c:
        row = c.execute("SELECT count(*) AS n FROM transactions WHERE ticker = %s", (ticker.upper(),)).fetchone()
    return row["n"]
