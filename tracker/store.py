"""Storage abstraction: Postgres when DATABASE_URL is set, JSON files otherwise.

Postgres is the source of truth. The file path is an offline-dev fallback only.
Downstream code (snapshot.py) calls these and never knows which backend is live.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import db, fundamentals, cache_source, quarterly
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


QUARTERLY_MAX_AGE_DAYS = 45  # routine confirm/refresh cadence for quarterly fundamentals


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _fresh_quarterly(ticker: str, earnings: dict | None) -> dict[str, Any] | None:
    """Our quarterly-derived fundamentals, refreshed if a newer quarter has been
    reported. The returned dict carries a 'stale' flag: stale=True means a newer
    quarter exists but its statement isn't available from the feed yet, so QoQ/margin
    must be treated as insufficient (no signal) rather than served as current.
    None if we have nothing and can't fetch."""
    row = db.fetch_fundamentals(ticker)
    last_date = _parse_date(earnings.get("last_date")) if earnings else None
    now = datetime.now(timezone.utc)
    report_date = row.get("report_date") if row else None
    fetched_at = row.get("fetched_at") if row else None

    if not quarterly.is_stale(report_date, fetched_at, last_date, now, QUARTERLY_MAX_AGE_DAYS):
        return {**row, "stale": False}

    # A newer quarter has actually been REPORTED than we hold (announcement is a full
    # cycle past our period end) — vs just an old cache that needs a confirming refresh.
    behind = (
        last_date is not None
        and report_date is not None
        and (last_date - report_date).days > quarterly.QUARTER_GAP_MAX_DAYS
    )
    rec = quarterly.record_from_quarters(quarterly.fetch_quarters(ticker))
    if rec is None:
        # fetch failed: keep old values; flag insufficient only if we KNOW a newer quarter exists
        return ({**row, "stale": behind} if row else None)
    advanced = report_date is None or (rec["report_date"] is not None and rec["report_date"] > report_date)
    if advanced or not behind:
        # advanced to a new quarter, or a routine refresh confirming the current one
        rec["source"] = "yfinance-quarterly"
        try:
            # upsert always bumps fetched_at; we call it only on advance / confirming
            # refresh, which is what resets the backstop clock (and avoids re-stale thrash).
            db.upsert_fundamentals(ticker, rec)
        except Exception:
            pass
        return {**rec, "stale": False}
    # behind, but the new statement isn't in the feed yet (lag): insufficient; retry next run
    return {**row, "stale": True}


def _apply_quarterly(d: dict[str, Any], q: dict[str, Any]) -> None:
    """Overlay the freshness-gated QoQ/margin onto a fundamentals dict (fill-null), or
    degrade them to None when the quarterly data is stale. Never touches TTM growth."""
    if q.get("stale"):
        d["revenue_qoq_pct"] = None
        d["gross_margin_qoq_pp"] = None
        d["gross_margin_yoy_pp"] = None
        d["fundamentals_stale"] = True
    else:
        for k in ("revenue_qoq_pct", "gross_margin_qoq_pp", "gross_margin_yoy_pp"):
            if d.get(k) is None and q.get(k) is not None:
                d[k] = q[k]
    if q.get("report_date") is not None:
        d["report_date"] = q["report_date"]


def _is_behind(report_date, earnings: dict | None) -> bool:
    """True if the latest earnings announcement is a full cycle past our period end
    (a newer quarter was reported than this data reflects)."""
    rd = _parse_date(report_date)
    last = _parse_date(earnings.get("last_date")) if earnings else None
    return bool(rd and last and (last - rd).days > quarterly.QUARTER_GAP_MAX_DAYS)


def get_fundamentals(ticker: str, earnings: dict | None = None, max_age_days: int = 7) -> dict[str, Any]:
    """Fundamentals, cheapest source first, with an earnings-aware freshness gate so the
    decision never runs on a stale quarter (applied to BOTH paths):
      1) equity-research cache (TTM growth, ~0 API cost) for covered names — QoQ/margin
         filled from our quarterly fetch, which refreshes when a new quarter is reported,
      2) our own fetch for the rest, cached in Neon, with the same staleness degrade.
    Pass `earnings` (the per-ticker dict with last_date) to enable the freshness gate.
    Always None-safe."""
    cached = cache_source.get_fundamentals(ticker)
    if cached:
        if db.using_db():
            q = _fresh_quarterly(ticker, earnings)
            if q is not None:
                _apply_quarterly(cached, q)
        return cached

    # 2) own fetch, with Neon caching — recompute when the cached row is behind a new
    #    report, and degrade QoQ/margin to insufficient if we're still behind (feed lag).
    if db.using_db():
        row = db.fetch_fundamentals(ticker)
        if row and row.get("fetched_at"):
            fresh = (datetime.now(timezone.utc) - row["fetched_at"]) < timedelta(days=max_age_days)
            if fresh and not _is_behind(row.get("report_date"), earnings):
                row.pop("fetched_at", None)
                row.pop("ticker", None)
                return row
        d = fundamentals.compute(ticker)
        try:
            db.upsert_fundamentals(ticker, d)
        except Exception:
            pass  # caching is best-effort; never block the run
        if _is_behind(d.get("report_date"), earnings):
            d["revenue_qoq_pct"] = None
            d["gross_margin_qoq_pp"] = None
            d["gross_margin_yoy_pp"] = None
            d["fundamentals_stale"] = True
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
