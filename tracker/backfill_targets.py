"""One-time / re-runnable patch: fill `price_target` (analyst low/median/mean/high
+ # analysts, from yfinance) into the CURRENT enriched snapshot, so the web app's
analyst-target range strip shows immediately without waiting for the next pipeline
run (every future run populates it natively via snapshot.build_ticker_row).

Does NOT touch narrative/enrichment — only adds the price_target field per ticker.

    python -m tracker.backfill_targets
"""
from __future__ import annotations

import json
import sys

from . import db, price_targets
from .config import load_env


def main(argv=None) -> int:
    load_env()
    if not db.using_db():
        print("No DB configured; nothing to backfill.")
        return 1

    with db.connect() as c:
        row = c.execute(
            "SELECT id, payload FROM snapshots WHERE payload->>'market_recap' IS NOT NULL "
            "ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        print("No enriched snapshot found.")
        return 1

    snap_id = row["id"]
    payload = row["payload"]
    tickers = payload.get("tickers", [])
    filled = 0
    for t in tickers:
        sym = t.get("ticker")
        if not sym:
            continue
        tgt = price_targets.fetch_target(sym)
        t["price_target"] = tgt
        if tgt:
            filled += 1
            up = (tgt.get("mean") or tgt.get("median"))
            print(f"  {sym:5} low {tgt['low']} / med {tgt.get('median')} / mean {tgt.get('mean')} / high {tgt['high']}"
                  f"  ({tgt.get('num_analysts')} analysts)")
        else:
            print(f"  {sym:5} no targets available")

    ok = db.update_snapshot(snap_id, payload)
    print(f"\nPatched snapshot id={snap_id}: {filled}/{len(tickers)} names got targets. update_ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
