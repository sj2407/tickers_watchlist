# tickers_watchlist

A twice-daily watchlist tracker that helps decide **pile on / trim / hold** across a
small book (~$200 per name, $200 floor when trimming). Runs **before market open**
and **after market close**.

## Architecture (three layers)

```
┌─ Python pipeline (dumb plumbing) ──────────────────────────────────────────┐
│  tracker/  →  fetch prices, returns, technicals, news, earnings, analyst    │
│              compute position math + rule-based signals  →  out/snapshot.json│
│  No LLM calls. Uses the equity-research-agent .env keys in place.            │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─ Routine (Claude on your subscription) ── see ROUTINE.md ───────────────────┐
│  Reads the snapshot, adds catalyst summaries, earnings recaps, the final     │
│  lean + rationale, market/macro context. Delivers email + push, writes DB.   │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─ Web app (phone-first, interactive) ── [next] ─────────────────────────────┐
│  Recap view → per-ticker drill-down → interactive charts → edit positions.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Why this split: the routine runs as a Claude Code agent, so the qualitative work
draws on the **Claude subscription**, not the pay-as-you-go API. The Python stays
pure data plumbing so it never spends API tokens.

## Run the pipeline

```bash
source .venv/bin/activate
python -m tracker.run --mode postclose --pretty   # or --mode preopen
```

Output: `out/snapshot.json`.

## Configure

- **`config.yaml`** — tickers, benchmark, signal thresholds.
- **`data/holdings.json`** — your positions (shares + avg cost basis). Source of truth
  for since-entry return, P/L, and weight-drift signals. Watch-only names can be omitted.
- **Secrets** — read from `~/equity-research-agent/.env` in place (never copied). Override
  the path with `WATCHLIST_ENV_FILE`, or set keys in the environment. `FINNHUB_API_KEY`
  powers news/earnings/analyst; price history uses free yfinance.

## What's in the snapshot

Per ticker: price (last/prev/day %), returns 1d/5d/20d, relative strength vs SPY,
technicals (20/50/200d MA + distance, RSI, ATR, 52w range, rel-volume, trend), full
position math, earnings (next date + estimates, last-quarter actuals + surprise),
analyst recommendation trend, recent news, and rule-based signal badges + a provisional
lean. The routine fills the `*_summary` / `*_recap` / `final_lean` / `rationale` fields.

## Data store (Postgres — the source of truth)

Standard Postgres (local Docker for dev → Neon/any host in prod, just a `DATABASE_URL`).
Schema in `migrations/` (forward-only, run with `python -m tracker.migrate`):

- **`transactions`** — append-only buy/sell ledger. Positions are *derived*, never
  overwritten. Size up = buy, trim = sell. Unlocks realized P/L, tax lots, history.
- **`current_positions`** — view deriving shares / avg cost / invested / realized P/L
  (average-cost method) from the ledger.
- **`watchlist`** — tracked tickers + metadata (editable from the app).
- **`snapshots`** — time-series of each run's enriched payload (JSONB).

```bash
docker run -d --name wl-pg -e POSTGRES_PASSWORD=watchlist -e POSTGRES_USER=watchlist \
  -e POSTGRES_DB=watchlist -p 5433:5432 -v wl_pgdata:/var/lib/postgresql/data postgres:17
python -m tracker.migrate    # apply migrations
python -m tracker.seed       # seed watchlist + opening trades (idempotent, live prices)
```

The pipeline reads watchlist/positions from Postgres and writes snapshots to it
(`tracker/store.py` picks DB when `DATABASE_URL` is set, else local JSON for offline dev).

## Web app (`web/`)

Next.js 16 + Tailwind + TypeScript, phone-first. Recap page → ticker drill-down with
an interactive candlestick chart (lightweight-charts) → in-app **position editor**
(quick ±$100/$200 trim/add, enforces the $200 floor, persists). Single-passcode gate
via `proxy.ts` (set `APP_PASSCODE`; unset = open in dev). Data layer reads **Neon
Postgres** when `DATABASE_URL` is set, else the pipeline's local JSON files.

```bash
cd web && npm run dev          # http://localhost:3000
# env: APP_PASSCODE=... DATABASE_URL=postgres://...  (.env.local)
```

DB schema + helpers in `web/src/lib/db.ts` (`initDb()`); data access in `web/src/lib/data.ts`.

## Status
- [x] Python data pipeline + signals
- [x] Holdings store + position math
- [x] Routine spec (`ROUTINE.md`)
- [x] Web app (Next.js, phone-first): recap, drill-down, interactive chart, editable positions
- [x] Qualitative layer: market recap, per-ticker takeaway/sentiment/catalyst/rationale (`tracker/enrich.py` + `out/enrichment.json`)
- [x] Earnings calendar + plain-English labels on every number
- [x] Single-passcode auth + Neon-or-file data layer (build + typecheck pass)
- [ ] Deploy to Vercel + provision Neon (needs Vercel login)
- [ ] Wire push alerts (ntfy) into the routine
- [ ] Wire the managed routine (schedule 09:00 / 16:30 ET)
