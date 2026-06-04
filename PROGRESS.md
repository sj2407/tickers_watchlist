# PROGRESS — tickers_watchlist

> Session-spanning log so a future session knows exactly what exists, why, and what's next.
> Map docs: `README.md` (overview), `ROUTINE.md` (what the scheduled routine does),
> `docs/PLAN-v2.md` (the v2 design + decisions + test plan). This file = status + roadmap.

## What this is
A twice-daily (heading toward intraday) tracker for a **small thematic satellite sleeve**
(~$200/name; >90% of the user's money is elsewhere in diversified ETFs). It helps decide
**pile-on / hold / trim / exit** per name. Sister tool: `~/equity-research-agent` =
*discovery* (Russell 3000 scoring, sectors/industries, market dynamics) that surfaces ideas;
this watchlist = *close tracking* of names already entered. They're complementary.

## Architecture (three layers)
1. **Python pipeline (`tracker/`)** — pure data plumbing, NO LLM calls. Fetches prices/returns/
   technicals/news/earnings/analyst/fundamentals, computes signals + the rule-based provisional
   lean, writes a snapshot. Entry: `python -m tracker.run --mode {preopen|postclose}`.
2. **Routine (Claude on the SUBSCRIPTION, not the API)** — reads the snapshot, writes the
   qualitative overlay to `out/enrichment.json` (takeaway, sentiment, catalyst, earnings recap,
   final lean, rationale, entry_guidance, invalidation, market recap), then `python -m
   tracker.enrich` merges + publishes. See `ROUTINE.md`.
3. **Web app (`web/`, Next.js 16)** — phone-first recap, ticker drill-downs (interactive chart
   w/ support/resistance, MACD/cross, fundamentals, thesis flags), in-app trim/add editor
   (transaction ledger), and a **/methodology** glossary tab. Deployed on Vercel.

## Deployed / live
- **App:** https://tickers-watchlist.vercel.app (Vercel Hobby, free). Passcode `APP_PASSCODE`=`AI2026`.
- **DB:** Neon Postgres (free), via Vercel integration → env var `WATCHLIST_DATABASE_URL`.
  Single source of truth: append-only `transactions` ledger → derived `current_positions`;
  time-series `snapshots` (JSONB); `watchlist`; `fundamentals` cache. Migrations in `migrations/`.
- **GitHub:** github.com/sj2407/tickers_watchlist (private). Secrets gitignored.
- **Routine (local, runs while the Claude app is open):** `~/.claude/scheduled-tasks/watchlist/`
  — ONE clock-branched job, cron `5 9,13,16 * * 1-5` (~9:14/1:14/4:14 ET, jitter). `--mode auto`
  resolves the session via `calendar_utils.resolve_mode`: premarket→preopen(full) · open→intraday
  (light entry-watch) · afterhours→postclose(full) · closed→no-op. (Old `watchlist-preopen`/
  `-postclose` are DISABLED but still in the scheduler registry — delete them in the Scheduled UI
  to free the slots; `rm` of their dirs alone doesn't de-register.)
- **Current book:** 21 tickers (18 @ $200 + NOW 8.63537sh + COHR 1.85723sh + LITE 0.63823sh).

## Data sources (tiered, efficiency-first)
- **equity-research-agent cache** (`~/equity-research-agent/data/cache.db`, read-only via
  `tracker/cache_source.py`): for ~18/21 names, reads FMP **fundamentals**, **earnings reactions
  (1d/5d)**, **factor scores** — ZERO API calls. Freshness-checked (per-type `meta` timestamps,
  ≤36h), schedule-agnostic, with standalone fallback. That repo refreshes daily ~9:30am ET.
- **Own fetch** (only for the 3 it doesn't cover + intraday): yfinance (prices, free), Finnhub
  (news/earnings/analyst), **FMP `/stable`** (v3 is now 403-legacy), yfinance `.info` for ADRs
  (ASML/TSM — FMP premium-gates them).
- **Keys** come from `~/equity-research-agent/.env` (loaded in place, never copied).

## The decision engine (the heart — see PLAN-v2 §4)
Quant rule layer proposes **pile_on / hold / trim** (caps at trim); the **LLM owns `exit`**.
- Trim = **confluence of ≥2 distinct deterioration dimensions** (downtrend, revenue weakening,
  margin compression, sustained negative relative strength, deteriorating earnings quality).
- **Size / % of book is NEVER a trim reason** (satellite sleeve). A single mild negative →
  hold; overbought → "don't chase" hold, never trim. Margin compression suppressed for
  hypergrowth unless severe (≤ −5pp). No sizing into a print. $200 floor on trims; exit closes fully.

## Durable rules (also in user memory)
- Recurring/LLM work → **subscription, not the paid API**.
- **Never use training-data facts** for prices/figures — only datasets/APIs or live web search.
- **Satellite sleeve:** trim/exit on thesis deterioration, never on position size.
- **Lead with narrative**, label every metric (hence the glossary).

## Status of v2 — MERGED & LIVE (2026-06-04)
Built in gated TDD phases, reviewed by 2 independent agents (plans + final code review), remediated,
verified e2e against Neon. **103 tests pass.** **Merged `v2-quant-and-glossary` → `main` (pushed to
GitHub) and redeployed to Vercel prod** — https://tickers-watchlist.vercel.app now serves the full
quant engine + glossary + fundamentals + intraday + live positions. Branch kept for history.

## Known tradeoffs / open items
- **TTM vs QoQ:** cache fundamentals are trailing-twelve-month, so QoQ sequential thesis-flags
  only fire for own-fetched names. Deterioration still caught via TTM-growth-negative + trend +
  RS + the LLM's earnings reads. Upgrade path: compute QoQ from the cache's `fundamentals_history`.
- **Intraday not yet limit-safe:** Finnhub (~63 calls/run: news+earnings+analyst) brushes the
  60/min free limit. **Next:** cache earnings-calendar + analyst daily (they don't change
  intraday) → only ~21 news calls/run → safe for several intraday refreshes.
- **FMP** is on a tier where v3 is dead and ADR quarterly is premium-gated; we work around it.
- Snapshot prices are last-close; a same-day move (e.g., AVGO −15%) shows in the narrative
  immediately but in the *number* on the next post-close run.

## Live position panel — SHIPPED
A recorded trade (add/trim via the editor → `transactions` ledger) reflects **instantly** in the
UI — `getLivePositions()` recomputes shares/avg-cost/invested/value/P&L/since-entry/weight + book
totals from `current_positions` + the latest snapshot price on every page load (drill-down + recap),
marked "● live". What still waits for a run: the live **price** (value is priced at the last run —
we don't quote on every page view) and the **analysis/lean** (re-scores at the next pipeline run).
File mode falls back to the snapshot figures.

## Intraday + caching — SHIPPED (on `v2-quant-and-glossary`, reviewed by 2 agents, remediated)
Single clock-branched routine; `api_cache` (per-ET-day) for earnings-cal + analyst; intraday is
a light **entry-watch** that fetches news ONLY for newly-triggered names (deduped once/ET-day) and
**carries narrative forward for all names — never nulls an output**; enrich-by-id (no clobber);
app reads only enriched rows. **Measured budget:** intraday Finnhub = #newly-triggered (0 on a calm
day), full run = 42; the equity-research cache covers fundamentals/scores/earnings-reactions for
18/21 at ~0 API cost. Equity refresh moved to **5:30 PM ET** (after close). 103 tests pass.
Known: cache gives TTM (not QoQ) for cache-covered names; FMP v3 dead → /stable for US, yfinance
.info for ADRs; old disabled routines need a UI delete to free slots.

## Roadmap / what's next
1. **Merge `v2-quant-and-glossary` → main + redeploy** (live site still shows v1 UI; DB has v2 data).
2. **Backtesting** — replay stored time-series `snapshots` to evaluate the decision engine: did
   pile_on/trim/exit calls precede good/bad forward returns? Tune thresholds against history.
3. **Portfolio-history charts** (every snapshot is stored — book value / position over time).
4. **Push/email alerts** for the intraday entry signals (delivery is currently the task notification).
5. **QoQ thesis flags for cache-covered names** via the equity cache's `fundamentals_history`.
6. **Sector-relative strength** (vs sector ETF, not just SPY).
7. Consider a paid FMP tier OR fuller reliance on the equity cache + Finnhub basics.

## Run / resume
```bash
cd ~/tickers_watchlist && source .venv/bin/activate
python -m tracker.migrate && python -m tracker.seed      # one-time DB setup
python -m tracker.run --mode postclose                   # pipeline → snapshot → Neon
python -m tracker.enrich                                  # merge out/enrichment.json → Neon
python -m pytest tests/ -q                                # 85 tests
cd web && npm run dev                                     # local app (reads Neon)
```
