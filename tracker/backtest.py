"""Backtest evaluator (P10) — replay stored snapshots and ask: did the leans
actually precede good/bad forward returns?

EVIDENCE-BUILDER, NOT A GATE (D2): the report prints sample sizes per cell and
REFUSES to print a conclusion under n < MIN_N — a 22-name sleeve accumulates
significance slowly and the report must never fake it.

Pure logic (`evaluate`) is separated from I/O: the CLI loads snapshots from
Postgres and fetches benchmark closes; tests inject synthetic ones.

No lookahead by construction: a decision dated D is scored ONLY with prices from
trading dates strictly after D (the entry leg is D's own price — the first price
the decision could have acted on); snapshots too close to the end of history
yield no sample rather than a shortened window.

Usage:
    python -m tracker.backtest            # markdown report to stdout
    python -m tracker.backtest --out backtest-report.md
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from typing import Any

MIN_N = 30          # below this, a cell reports its stats but draws no conclusion
WINDOWS = (5, 20)   # forward trading-day horizons


# ── pure evaluation ────────────────────────────────────────────────────────

def _price_by_date(snapshots: list[dict]) -> dict[str, dict[date, float]]:
    """{ticker: {as_of_date: last_price}} — latest snapshot per date wins."""
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for snap in sorted(snapshots, key=lambda s: str(s.get("generated_at", ""))):
        d = _d(snap.get("as_of_date"))
        if d is None:
            continue
        for t in snap.get("tickers", []):
            px = (t.get("price") or {}).get("last")
            if px:
                out[t["ticker"]][d] = float(px)
    return out


def _d(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def _fwd(prices: dict[date, float], d0: date, n: int) -> float | None:
    """Forward return over n TRADING dates present in the history, strictly after
    d0. None when there isn't enough future data (never a shortened window)."""
    dates = sorted(prices)
    if d0 not in prices:
        return None
    i = dates.index(d0)
    if i + n >= len(dates):
        return None
    return (prices[dates[i + n]] / prices[d0] - 1.0) * 100.0


def evaluate(snapshots: list[dict], bench: dict[date, float] | None = None) -> dict[str, Any]:
    """Score every (snapshot, ticker, lean) decision against forward returns.

    Returns {"leans": {lean: {n, avg_fwd5, avg_fwd20, avg_excess20, hit_rate}},
             "dimensions": {dim: {...}}, "decisions": n_total}.
    hit semantics: pile_on succeeds when fwd20 beats the benchmark (or >0 with no
    benchmark); trim/exit succeed when fwd20 LAGS it (reducing was right); hold
    and watch are tracked but have no hit semantics (hit_rate None).
    Each (ticker, as_of_date) is scored once — the latest snapshot that day.
    """
    prices = _price_by_date(snapshots)
    by_day: dict[tuple[str, date], dict] = {}
    for snap in sorted(snapshots, key=lambda s: str(s.get("generated_at", ""))):
        d0 = _d(snap.get("as_of_date"))
        if d0 is None:
            continue
        for t in snap.get("tickers", []):
            lean = t.get("final_lean") or (t.get("signals") or {}).get("provisional_lean")
            if not lean:
                continue
            dims = ((t.get("signals") or {}).get("drivers") or {}).get("deterioration", [])
            by_day[(t["ticker"], d0)] = {"lean": lean, "dims": list(dims)}

    lean_rows: dict[str, list[dict]] = defaultdict(list)
    dim_rows: dict[str, list[dict]] = defaultdict(list)
    for (tk, d0), info in by_day.items():
        f5 = _fwd(prices.get(tk, {}), d0, 5)
        f20 = _fwd(prices.get(tk, {}), d0, 20)
        if f5 is None and f20 is None:
            continue  # end of history — no sample, never a shortened window
        b20 = _fwd(bench, d0, 20) if bench else None
        excess20 = (f20 - b20) if (f20 is not None and b20 is not None) else None
        row = {"f5": f5, "f20": f20, "excess20": excess20}
        lean_rows[info["lean"]].append(row)
        for dim in info["dims"]:
            dim_rows[dim].append(row)

    def _agg(rows: list[dict], lean: str | None = None) -> dict[str, Any]:
        def avg(key):
            vals = [r[key] for r in rows if r[key] is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        hit = None
        if lean in ("pile_on", "trim", "exit"):
            scored = [r for r in rows if (r["excess20"] is not None or r["f20"] is not None)]
            if scored:
                def won(r):
                    m = r["excess20"] if r["excess20"] is not None else r["f20"]
                    return m > 0 if lean == "pile_on" else m < 0
                hit = round(sum(1 for r in scored if won(r)) / len(scored) * 100, 1)
        return {"n": len(rows), "avg_fwd5": avg("f5"), "avg_fwd20": avg("f20"),
                "avg_excess20": avg("excess20"), "hit_rate": hit}

    return {
        "decisions": sum(len(v) for v in lean_rows.values()),
        "leans": {k: _agg(v, k) for k, v in sorted(lean_rows.items())},
        "dimensions": {k: _agg(v) for k, v in sorted(dim_rows.items())},
    }


def render_report(result: dict[str, Any]) -> str:
    """Markdown report with the n<MIN_N honesty rule baked in."""
    lines = ["# Backtest report — lean vs forward returns", "",
             f"Decisions scored: **{result['decisions']}** "
             f"(cells under n={MIN_N} show stats but draw NO conclusion)", "",
             "_Both legs are price returns (snapshot prices vs raw benchmark closes; "
             "dividends excluded on both sides)._", ""]

    def section(title, table: dict, with_hit: bool):
        lines.append(f"## {title}")
        hdr = "| | n | fwd 5d | fwd 20d | excess 20d vs SPY |" + (" hit rate |" if with_hit else "")
        sep = "|---|---|---|---|---|" + ("---|" if with_hit else "")
        lines.extend([hdr, sep])
        for key, s in table.items():
            row = (f"| {key} | {s['n']} | {_fmt(s['avg_fwd5'])} | {_fmt(s['avg_fwd20'])} "
                   f"| {_fmt(s['avg_excess20'])} |")
            if with_hit:
                row += f" {_fmt(s['hit_rate'], '%')} |"
            lines.append(row)
        for key, s in table.items():
            if s["n"] < MIN_N:
                lines.append(f"- `{key}`: n={s['n']} — **insufficient sample, no conclusion**.")
            elif with_hit and s.get("hit_rate") is not None:
                verdict = "predictive" if s["hit_rate"] > 55 else \
                          "anti-predictive" if s["hit_rate"] < 45 else "indistinguishable from noise"
                lines.append(f"- `{key}`: n={s['n']}, hit rate {s['hit_rate']}% — {verdict} at this sample size.")
        lines.append("")

    section("By lean", result["leans"], with_hit=True)
    section("By deterioration dimension (forward returns after the flag fired)",
            result["dimensions"], with_hit=False)
    return "\n".join(lines)


def _fmt(v, suffix=""):
    return "—" if v is None else f"{v:+.2f}{suffix}" if suffix != "%" else f"{v:.1f}%"


# ── I/O (CLI only — tests never touch this) ────────────────────────────────

def _load_snapshots() -> list[dict]:
    from . import db

    if not db.using_db():
        raise SystemExit("DATABASE_URL not set — the backtest replays stored Neon snapshots.")
    with db.connect() as c:
        rows = c.execute("SELECT payload FROM snapshots ORDER BY generated_at").fetchall()
    return [r["payload"] for r in rows]


def _bench_closes(symbol: str = "SPY") -> dict[date, float]:
    # RAW closes, deliberately: the ticker legs are snapshot prices (price
    # returns, no dividends), so the benchmark leg must match or excess20 is
    # biased against the sleeve by SPY's dividend yield (review R1-4).
    from . import sources

    hist = sources.price_history(symbol, days=400)
    if hist.empty:
        return {}
    closes = hist["Close"].dropna()
    return {ts.date(): float(v) for ts, v in closes.items()}


def main(argv=None) -> int:
    from .config import load_env

    p = argparse.ArgumentParser(description="Replay stored snapshots; score the leans.")
    p.add_argument("--out", default=None, help="write the markdown report here (default: stdout)")
    args = p.parse_args(argv)
    load_env()
    report = render_report(evaluate(_load_snapshots(), _bench_closes()))
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(report)
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
