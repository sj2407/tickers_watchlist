"""Average-cost position fold — the pure-Python reference for the
`current_positions` SQL view (migration 0006). One source of truth for the math;
the integration test asserts the SQL view reproduces this fold row-for-row.

Average-cost method:
- a BUY re-averages cost over (remaining shares + new shares); fees capitalize
  into cost (same convention as the original view: buys cost `shares*price+fees`).
- a SELL leaves avg cost unchanged and realizes `matched*(price - avg) - fees`,
  where `matched = min(sold, held)` — an oversell clamps to the held quantity
  (never negative shares) but its fees still subtract (they're real costs).
- a position that reaches 0 shares resets: cost drops to 0 and the next buy
  seeds a fresh average (the historical buys no longer pollute it).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Txn:
    side: str            # "buy" | "sell"
    shares: float
    price: float
    fees: float = 0.0


def fold(txns: Iterable[Txn]) -> dict[str, Any]:
    """Fold transactions (already in execution order) into the position.
    Returns {shares, avg_cost (None when flat), invested, realized_pl}."""
    shares = 0.0
    cost = 0.0
    realized = 0.0
    for t in txns:
        if t.side == "buy":
            shares += t.shares
            cost += t.shares * t.price + t.fees
        else:  # sell
            matched = min(t.shares, shares)
            if matched > 0:
                avg = cost / shares
                realized += matched * (t.price - avg)
                shares -= matched
                cost = shares * avg
            realized -= t.fees
            if shares <= 0:
                shares, cost = 0.0, 0.0
    return {
        "shares": shares,
        "avg_cost": (cost / shares) if shares > 0 else None,
        "invested": cost,
        "realized_pl": realized,
    }
