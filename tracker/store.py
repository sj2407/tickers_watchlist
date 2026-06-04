"""Storage abstraction: Postgres when DATABASE_URL is set, JSON files otherwise.

Postgres is the source of truth. The file path is an offline-dev fallback only.
Downstream code (snapshot.py) calls these and never knows which backend is live.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import db, fundamentals, cache_source
from .config import load_config
from .holdings import load_holdings  # JSON fallback


def backend() -> str:
    return "postgres" if db.using_db() else "file"


def get_tickers() -> list[str]:
    if db.using_db():
        rows = db.fetch_watchlist(active_only=True)
        if rows:
            return [r["ticker"].upper() for r in rows]
    return [t.upper() for t in load_config().get("tickers", [])]


def get_holdings() -> dict[str, dict[str, Any]]:
    if db.using_db():
        return db.fetch_positions()
    return load_holdings()


def _write_file(snap: dict[str, Any]) -> None:
    import json
    from pathlib import Path

    out = Path(__file__).resolve().parent.parent / "out" / "snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, default=str))


def get_market_extras(ticker: str) -> dict[str, Any]:
    """Slow extras from the equity-research cache (earnings reaction + factor scores).
    Empty dict if the cache is unavailable/stale/uncovered — purely additive."""
    return {
        "earnings_reaction": cache_source.get_earnings_reaction(ticker),
        "scores": cache_source.get_scores(ticker),
    }


def get_fundamentals(ticker: str, max_age_days: int = 7) -> dict[str, Any]:
    """Fundamentals, cheapest source first:
      1) equity-research cache (fresh FMP data, ~0 API cost) for covered names,
      2) our own fetch (FMP /stable + yfinance fallback), cached in Neon.
    Always None-safe."""
    # 1) shared cache (covers ~18/21; freshness-checked inside)
    cached = cache_source.get_fundamentals(ticker)
    if cached:
        return cached

    # 2) own fetch, with Neon caching
    if db.using_db():
        row = db.fetch_fundamentals(ticker)
        if row and row.get("fetched_at"):
            age = datetime.now(timezone.utc) - row["fetched_at"]
            if age < timedelta(days=max_age_days):
                row.pop("fetched_at", None)
                row.pop("ticker", None)
                return row
        d = fundamentals.compute(ticker)
        try:
            db.upsert_fundamentals(ticker, d)
        except Exception:
            pass  # caching is best-effort; never block the run
        return d
    return fundamentals.compute(ticker)


def get_latest_enriched() -> dict[str, Any] | None:
    """The latest snapshot that already has narrative — used for carry-forward.
    DB → snapshots with market_recap set; file → out/snapshot.json if it's enriched."""
    if db.using_db():
        return db.get_latest_enriched()
    import json
    from pathlib import Path

    f = Path(__file__).resolve().parent.parent / "out" / "snapshot.json"
    try:
        snap = json.loads(f.read_text())
        return snap if snap.get("market_recap") else None
    except Exception:
        return None


def write_snapshot(snap: dict[str, Any], mode: str) -> int | None:
    """Insert a fresh snapshot. Returns the new row id (DB) so enrich can update THAT
    row (no cross-run clobber). File mode → rewrite out/snapshot.json, returns None."""
    if db.using_db():
        as_of = date.fromisoformat(snap["as_of_date"])
        gen = datetime.fromisoformat(snap["generated_at"])
        return db.insert_snapshot(snap, mode, as_of, gen)
    _write_file(snap)
    return None


def publish_enriched(snap: dict[str, Any], snapshot_id: int | None = None) -> None:
    """Publish the enriched snapshot. DB → update the SPECIFIC inserted row by id (falls
    back to latest only if no id); file → rewrite out/snapshot.json."""
    if db.using_db():
        if snapshot_id is not None and db.update_snapshot(snapshot_id, snap):
            return
        if not db.update_latest_snapshot(snap):
            db.insert_snapshot(snap, snap.get("mode", "postclose"),
                               date.fromisoformat(snap["as_of_date"]),
                               datetime.fromisoformat(snap["generated_at"]))
        return
    _write_file(snap)
