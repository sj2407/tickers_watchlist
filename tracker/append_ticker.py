"""Append (or refresh) ONE ticker into the latest snapshot without re-fetching the others.

Fetches just the given symbol's full data (price history → technicals, fundamentals,
analyst, news, earnings, signals, position), splices its row into the current board,
recomputes the portfolio + weights, and republishes to Neon. The deployed app reads
Neon, so it shows up on the next page load — no redeploy, no full refresh.

    python -m tracker.append_ticker HIMS

Narrative (takeaway/lean) is still the routine's job — run `tracker.enrich` after with an
enrichment.json containing just this ticker, or let the next full run narrate it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import sources, store
from .config import load_config, load_env
from .snapshot import build_ticker_row, _portfolio_block

OUT = Path(__file__).resolve().parent.parent / "out"


def append_ticker(tk: str) -> tuple[dict, dict]:
    load_env()
    cfg = load_config()
    tz = cfg["timezone"]
    today = datetime.now(ZoneInfo(tz)).date()

    prior = store.get_latest_enriched()
    if not prior:
        raise SystemExit("No enriched snapshot to append to — run the full pipeline first.")

    holdings = store.get_holdings()
    bench_hist = sources.price_history(cfg["benchmark"], cfg["history_days"])
    h = sources.price_history(tk, cfg["history_days"])
    q = sources.fast_quote(tk)
    last = q.get("last_price")
    if last is None and not h.empty:
        last = round(float(h["Close"].dropna().iloc[-1]), 2)

    # book = the existing board's held value (excluding tk) + this ticker's value
    book = sum((t.get("position", {}).get("market_value") or 0) for t in prior["tickers"]
               if t.get("position", {}).get("held") and t["ticker"] != tk)
    hold = holdings.get(tk)
    if hold and last:
        book += float(hold.get("shares") or 0) * last

    row = build_ticker_row(tk, h, q, last, cfg, today, bench_hist, book, holdings, mode="postclose")
    row["news"] = sources.company_news(tk, cfg["news_lookback_days"], cfg["max_news_per_ticker"])

    merged = [t for t in prior["tickers"] if t["ticker"] != tk] + [row]
    snap = dict(prior)
    snap["tickers"] = merged
    snap["generated_at"] = datetime.now(ZoneInfo(tz)).isoformat()
    snap["as_of_date"] = today.isoformat()
    snap["portfolio"] = _portfolio_block(merged, book)
    snap["needs_full_enrichment"] = False
    snap["intraday_triggered"] = []
    for t in merged:                       # weights shift when the book grows
        mv = t.get("position", {}).get("market_value")
        if mv is not None and book:
            t["position"]["weight_pct"] = round(mv / book * 100, 2)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "snapshot.json").write_text(json.dumps(snap, default=str))
    sid = store.write_snapshot(snap, "postclose")   # new enriched row (carries prior market_recap)
    if sid is not None:
        (OUT / ".snapshot_id").write_text(str(sid))
    return snap, row


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Append one ticker (no full refresh).")
    p.add_argument("ticker")
    args = p.parse_args(argv)
    snap, row = append_ticker(args.ticker.upper())
    t, f, pos = row["technicals"], (row.get("fundamentals") or {}), row["position"]
    print(f"appended {row['ticker']}: ${row['price']['last']} · RSI {t.get('rsi14')} · {t.get('trend')} · "
          f"rev_yoy {f.get('revenue_yoy')} · pe {f.get('pe')} · lean {row['signals']['provisional_lean']} · "
          f"pos {pos.get('shares')}sh since {pos.get('since_entry_pct')}% · {len(snap['tickers'])} tickers on board")
    return 0


if __name__ == "__main__":
    sys.exit(main())
