"""Apply the routine's qualitative overlay onto a snapshot.

The Claude routine (on the subscription) reads out/snapshot.json, then writes
out/enrichment.json with the *words* — market recap, macro context, and per-ticker
takeaway / sentiment / catalyst summary / earnings recap / final lean / rationale.
This merges that overlay back into the snapshot the app reads. Kept as a tiny,
deterministic step so the reasoning stays in the routine, not in Python.

enrichment.json shape:
{
  "market": {"recap": "...", "macro": "..."},
  "tickers": {
    "AAPL": {
      "takeaway": "...", "sentiment": "bullish|bearish|neutral|mixed",
      "catalyst_summary": "...", "earnings_recap": "... or null",
      "final_lean": "pile_on|hold|trim|exit|watch", "rationale": "...",
      "entry_guidance": "... or null", "invalidation": "... or null"
    }
  }
}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "out" / "snapshot.json"
ENRICHMENT = ROOT / "out" / "enrichment.json"

_TICKER_FIELDS = (
    "takeaway",
    "sentiment",
    "catalyst_summary",
    "earnings_recap",
    "final_lean",
    "rationale",
    "entry_guidance",
    "invalidation",
)


def apply_enrichment(snapshot_path: Path = SNAPSHOT, enrichment_path: Path = ENRICHMENT) -> dict:
    snap = json.loads(snapshot_path.read_text())
    if not enrichment_path.exists():
        return snap
    enr = json.loads(enrichment_path.read_text())

    market = enr.get("market", {})
    if market.get("recap") is not None:
        snap["market_recap"] = market["recap"]
    if market.get("macro") is not None:
        snap["macro_context"] = market["macro"]

    by_ticker = {k.upper(): v for k, v in (enr.get("tickers") or {}).items()}
    for row in snap.get("tickers", []):
        e = by_ticker.get(row["ticker"].upper())
        if not e:
            continue
        for f in _TICKER_FIELDS:
            if f in e:
                row[f] = e[f]
        if "final_lean" in e:
            # The routine took a fresh stance on this name: old validation
            # provenance no longer applies (validate_leans below re-flags if the
            # NEW lean is also invalid).
            row["lean_coerced_from"] = None
            row["lean_rejected"] = None

    # Enforce the action vocabulary on ALL rows (overlaid AND carried) — see
    # signals.validate_leans. Never trust the LLM's labels blindly.
    from . import signals

    signals.validate_leans(snap)

    snapshot_path.write_text(json.dumps(snap, indent=2, default=str))

    # publish to the source of truth, targeting the row this run inserted (no clobber)
    from . import store

    id_file = snapshot_path.parent / ".snapshot_id"
    snapshot_id = None
    if id_file.exists():
        try:
            snapshot_id = int(id_file.read_text().strip())
        except ValueError:
            snapshot_id = None
    store.publish_enriched(snap, snapshot_id)
    return snap


if __name__ == "__main__":
    from .config import load_env
    load_env()
    p = argparse.ArgumentParser(description="Merge enrichment overlay into the snapshot.")
    p.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    p.add_argument("--enrichment", type=Path, default=ENRICHMENT)
    args = p.parse_args()
    snap = apply_enrichment(args.snapshot, args.enrichment)
    n = sum(1 for t in snap["tickers"] if t.get("takeaway"))
    print(f"Applied enrichment → {n}/{len(snap['tickers'])} tickers, market_recap={'set' if snap.get('market_recap') else 'empty'}")
