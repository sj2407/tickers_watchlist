"""CLI entrypoint for the data pipeline.

Usage:
    python -m tracker.run --mode preopen
    python -m tracker.run --mode postclose
    python -m tracker.run --mode preopen --out out/snapshot.json

Writes the snapshot JSON. The Claude routine then reads it, adds the qualitative
layer (catalyst summaries, earnings recap, final lean), and updates the app.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .snapshot import build_snapshot
from . import store

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "out" / "snapshot.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Watchlist data pipeline (dumb layer).")
    p.add_argument("--mode", choices=["preopen", "intraday", "postclose", "auto"], required=True)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--pretty", action="store_true", help="indent the JSON output")
    args = p.parse_args(argv)

    mode = args.mode
    if mode == "auto":
        from .calendar_utils import resolve_mode
        mode = resolve_mode()
        if mode is None:
            print("[auto] market closed — no-op (nothing fetched or written).")
            return 0
        print(f"[auto] resolved mode → {mode}")

    snap = build_snapshot(mode)
    # working file (always) — the enrich step reads this
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(snap, f, indent=2 if args.pretty else None, default=str)
    # publish to the source of truth (Postgres if configured, else file)
    store.write_snapshot(snap, mode)

    n = len(snap.get("tickers", []))
    pf = snap.get("portfolio", {})
    print(f"[{mode}] {store.backend()} · {n} tickers · "
          f"book ${pf.get('book_value')} · unrealized ${pf.get('unrealized_pl')}")
    alerts = snap.get("alerts", [])
    if alerts:
        print(f"  {len(alerts)} mechanical alert(s):")
        for a in alerts:
            print(f"   • {a['msg']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
