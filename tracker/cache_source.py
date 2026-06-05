"""Read-only access to equity-research-agent's local cache for SLOW data.

That project runs a daily ~9:30am ET refresh that already pulls FMP fundamentals,
earnings actuals (+ 1d/5d price reactions), and factor scores for the Russell 3000.
~18 of our 21 tickers are covered, so reading from here avoids re-hitting the APIs.

Discipline:
- READ ONLY. Opens the SQLite file read-only; never writes.
- Freshness-checked + schedule-agnostic: we trust a data type only if its `meta`
  timestamp is within tolerance. If the cache is absent, stale, or the ticker isn't
  covered, the function returns None and the caller fetches it itself (standalone fallback).
- Point elsewhere with EQUITY_CACHE_DB; disable entirely with WATCHLIST_USE_CACHE=0.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CACHE_DB = os.environ.get(
    "EQUITY_CACHE_DB", str(Path.home() / "equity-research-agent" / "data" / "cache.db")
)
DEFAULT_MAX_AGE_HOURS = 36  # tolerant of a late/missed daily run before we self-fetch

# cache metric key -> (our field, scale)  [FMP ratios are fractions → ×100 for %]
_FUND_MAP = {
    "revenue_growth_ttm": ("revenue_yoy", 100.0),
    "eps_growth_ttm": ("eps_yoy", 100.0),
    "gross_margin": ("gross_margin", 100.0),
    "pe_ratio": ("pe", 1.0),
    "eps_ttm": ("eps_ttm", 1.0),
    "net_margin": ("net_margin", 100.0),
    "forward_pe": ("forward_pe", 1.0),
}


def enabled() -> bool:
    return os.environ.get("WATCHLIST_USE_CACHE", "1") != "0"


def available() -> bool:
    return enabled() and Path(CACHE_DB).is_file()


def _connect() -> sqlite3.Connection | None:
    if not available():
        return None
    try:
        conn = sqlite3.connect(f"file:{CACHE_DB}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None


def _meta_time(conn: sqlite3.Connection, key: str) -> datetime | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if not row or not row[0]:
        return None
    try:
        dt = datetime.fromisoformat(row[0])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_fresh(conn: sqlite3.Connection, meta_key: str, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> bool:
    ts = _meta_time(conn, meta_key)
    if ts is None:
        return False
    return (datetime.now(timezone.utc) - ts) <= timedelta(hours=max_age_hours)


def get_fundamentals(ticker: str, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> dict[str, Any] | None:
    """Map the cache's latest FMP fundamentals to our schema. None if absent/stale.
    Note: growth here is TTM (more stable than single-quarter YoY); flagged in source."""
    conn = _connect()
    if conn is None:
        return None
    try:
        if not is_fresh(conn, "fmp_refreshed_at", max_age_hours):
            return None
        # Latest value PER METRIC (a ticker's metrics span multiple fetched_at
        # batches — yfinance vs FMP — so a single global max() drops half of them).
        rows = conn.execute(
            "SELECT f.metric, f.value FROM fundamentals f "
            "WHERE f.ticker = ? AND f.fetched_at = ("
            "  SELECT max(f2.fetched_at) FROM fundamentals f2 "
            "  WHERE f2.ticker = f.ticker AND f2.metric = f.metric)",
            (ticker.upper(),),
        ).fetchall()
        if not rows:
            return None
        raw = {r["metric"]: r["value"] for r in rows}
        out: dict[str, Any] = {"source": "equity-cache(fmp,ttm)"}
        for ck, (field, scale) in _FUND_MAP.items():
            v = raw.get(ck)
            out[field] = round(v * scale, 4) if isinstance(v, (int, float)) else None
        # The cache rarely stores eps_growth_ttm but usually has earnings_growth_ttm
        # (net-income growth, a close proxy). Use it as a fallback so EPS growth isn't blank.
        if out.get("eps_yoy") is None and isinstance(raw.get("earnings_growth_ttm"), (int, float)):
            out["eps_yoy"] = round(raw["earnings_growth_ttm"] * 100.0, 4)
        # thesis inputs the cache can support (QoQ margin isn't in this table → None)
        out["revenue_qoq_pct"] = None
        out["gross_margin_qoq_pp"] = None
        return out
    finally:
        conn.close()


def get_earnings_reaction(ticker: str, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> dict[str, Any] | None:
    """Latest reported quarter: EPS surprise + 1d/5d price reaction."""
    conn = _connect()
    if conn is None:
        return None
    try:
        if not is_fresh(conn, "actuals_refreshed_at", max_age_hours):
            return None
        r = conn.execute(
            "SELECT report_date, eps_actual, eps_estimate, eps_surprise_pct, "
            "revenue_surprise_pct, price_reaction_1d, price_reaction_5d "
            "FROM earnings_actuals WHERE ticker = ? ORDER BY report_date DESC LIMIT 1",
            (ticker.upper(),),
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_scores(ticker: str, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> dict[str, Any] | None:
    """Factor z-scores (growth/quality/momentum/value/health) + composite rank."""
    conn = _connect()
    if conn is None:
        return None
    try:
        if not is_fresh(conn, "scores_computed_at", max_age_hours):
            return None
        r = conn.execute(
            "SELECT value_z, quality_z, growth_z, health_z, momentum_z, composite, rank "
            "FROM scores WHERE ticker = ? ORDER BY as_of DESC LIMIT 1",
            (ticker.upper(),),
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()
