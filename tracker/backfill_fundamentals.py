"""One-time / re-runnable backfill of quarterly fundamentals (Rev QoQ, margin QoQ,
report date) for the cache-covered watchlist names, which the TTM cache leaves blank.

Free (yfinance). Safe to re-run. The live pipeline also self-refreshes a name whenever
a newer quarter is reported (see store._fresh_quarterly), so this is mainly to
pre-populate and to verify.

    python -m tracker.backfill_fundamentals            # backfill
    python -m tracker.backfill_fundamentals --verify   # backfill + freshness audit
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

from . import store, db, cache_source, quarterly, sources
from .config import load_env, load_config


def _last_earnings(tk: str) -> date | None:
    """Latest reported (past) earnings date (for the freshness audit)."""
    try:
        today = datetime.now().date()
        past = [d for d in (sources.earnings_dates_yf(tk) or []) if d <= today]
        return max(past) if past else None
    except Exception:
        return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backfill quarterly fundamentals (yfinance, free).")
    p.add_argument("--verify", action="store_true", help="cross-check report_date vs latest earnings")
    args = p.parse_args(argv)

    load_env()
    load_config()
    if not db.using_db():
        print("No DB configured; nothing to backfill.")
        return 1

    tickers = store.get_tickers()
    done = skipped = 0
    audit_flags = []
    for tk in tickers:
        covered = cache_source.get_fundamentals(tk) is not None
        if not covered:
            skipped += 1
            print(f"  {tk:5} uncovered (own-fetch already provides QoQ) — skip")
            continue
        rec = quarterly.record_from_quarters(quarterly.fetch_quarters(tk))
        if not rec or rec.get("report_date") is None:
            print(f"  {tk:5} no quarterly data from yfinance — skip")
            continue
        rec["source"] = "yfinance-quarterly"
        db.upsert_fundamentals(tk, rec)
        done += 1
        line = (f"  {tk:5} report {rec['report_date']} · rev_qoq {rec['revenue_qoq_pct']} · "
                f"margin_qoq {rec['gross_margin_qoq_pp']} · eps_yoy {rec['eps_yoy']}")
        if args.verify:
            last = _last_earnings(tk)
            gap = (last - rec["report_date"]).days if last else None
            stale = gap is not None and gap > quarterly.QUARTER_GAP_MAX_DAYS
            line += f"  | last_earnings {last} gap {gap}d{'  ⚠ STALE' if stale else ''}"
            if stale:
                audit_flags.append((tk, rec["report_date"], last, gap))
        print(line)

    print(f"\nbackfilled {done}, skipped {skipped}")
    if args.verify:
        if audit_flags:
            print("⚠ freshness audit flagged (a newer quarter likely reported than yfinance has):")
            for tk, rd, last, gap in audit_flags:
                print(f"   {tk}: have {rd}, last earnings {last} ({gap}d gap)")
        else:
            print("freshness audit: all backfilled names look current (report_date within a cycle of last earnings).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
