"""Positions store — the source of truth for cost basis & size.

v1 is a local JSON file you (or the web app) edit. When we move to the deployed
Vercel app this is the one module that gets swapped for a DB-backed reader; the
shape stays identical so nothing downstream changes.

Shape (data/holdings.json):
    {
      "AAPL": {"shares": 1.2, "cost_basis": 165.40, "notes": "core", "target": 220, "stop": 150},
      ...
    }
cost_basis is the average cost *per share*. Omit a ticker (or shares=0) to track
it as a watch-only name with no position math.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOLDINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "holdings.json"


def load_holdings() -> dict[str, dict[str, Any]]:
    if not HOLDINGS_FILE.exists():
        return {}
    try:
        with open(HOLDINGS_FILE) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return {k.upper(): v for k, v in raw.items() if isinstance(v, dict)}


def save_holdings(holdings: dict[str, dict[str, Any]]) -> None:
    HOLDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLDINGS_FILE, "w") as f:
        json.dump({k.upper(): v for k, v in holdings.items()}, f, indent=2, sort_keys=True)
