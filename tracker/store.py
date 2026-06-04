"""Storage abstraction: Postgres when DATABASE_URL is set, JSON files otherwise.

Postgres is the source of truth. The file path is an offline-dev fallback only.
Downstream code (snapshot.py) calls these and never knows which backend is live.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from . import db
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


def write_snapshot(snap: dict[str, Any], mode: str) -> None:
    """Publish a fresh snapshot (insert). Postgres → snapshots row; file → out/snapshot.json."""
    if db.using_db():
        as_of = date.fromisoformat(snap["as_of_date"])
        gen = datetime.fromisoformat(snap["generated_at"])
        db.insert_snapshot(snap, mode, as_of, gen)
        return
    _write_file(snap)


def publish_enriched(snap: dict[str, Any]) -> None:
    """Publish the enriched snapshot. Postgres → update latest row; file → rewrite file."""
    if db.using_db():
        if not db.update_latest_snapshot(snap):
            # no row yet (enrich ran before a pipeline insert) → insert one
            db.insert_snapshot(snap, snap.get("mode", "postclose"),
                               date.fromisoformat(snap["as_of_date"]),
                               datetime.fromisoformat(snap["generated_at"]))
        return
    _write_file(snap)
