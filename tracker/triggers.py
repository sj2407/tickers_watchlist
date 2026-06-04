"""Intraday entry-watch triggers — pure functions over a snapshot ticker row.

Purpose: on a light intraday run, flag the 0-few names worth a look for ENTRY timing
(a dip into a buy zone, or a notable drop on a name whose thesis is intact). Deliberately
conservative: never fires on up moves, never when overbought, never on a deteriorating
(trim/exit) name. The routine narrates + alerts only the flagged names.
"""
from __future__ import annotations

from typing import Any


def compute_triggers(row: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    it = cfg.get("intraday") or {}
    near_support_pct = it.get("near_support_pct", 2.0)
    rsi_buy = it.get("rsi_buy_band", 45.0)
    z_lo, z_hi = it.get("sma50_zone_low", -4.0), it.get("sma50_zone_high", 1.0)
    dip = it.get("notable_dip_pct", -5.0)
    overbought = (cfg.get("signals") or {}).get("rsi_overbought", 70)

    pos = row.get("position") or {}
    tech = row.get("technicals") or {}
    tb = row.get("thesis_break") or {}
    sig = row.get("signals") or {}
    price = row.get("price") or {}

    held = bool(pos.get("held")) and (pos.get("shares") or 0) > 0
    lean = row.get("final_lean") or sig.get("provisional_lean")
    thesis_ok = not tb.get("any")
    day = price.get("day_change_pct")
    rsi = tech.get("rsi14")

    triggers: list[str] = []

    # entry zone — a name you'd add to (pile_on/hold, thesis intact), dipping into a buy
    # setup. Requires a flat/down day and NOT overbought (never chase strength).
    if (lean in ("pile_on", "hold") and thesis_ok
            and (day is None or day <= 0)
            and not (rsi is not None and rsi >= overbought)):
        near_support = tech.get("support_dist_pct") is not None and tech["support_dist_pct"] <= near_support_pct
        d50 = tech.get("dist_sma50_pct")
        at_50d_zone = d50 is not None and z_lo <= d50 <= z_hi
        rsi_cooled = rsi is not None and rsi <= rsi_buy
        if near_support or at_50d_zone or rsi_cooled:
            triggers.append("entry_zone")

    # notable dip — held name down hard today but thesis intact ("your entry, or watch?")
    if held and thesis_ok and day is not None and day <= dip:
        triggers.append("notable_dip")

    return triggers
