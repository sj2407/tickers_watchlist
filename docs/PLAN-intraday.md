# Plan — intraday refreshes, cadence-aware caching, single routine

**Branch:** `v2-quant-and-glossary` (continues the v2 work) · **Status:** PLAN (nothing built yet)
**Workflow:** plan → implement (TDD, gated) → verify budget → review → merge.

## Goal
Move from 2 fixed routines (pre-open + post-close) to **one clock-branched routine** that
fires a few times/day, where **intraday runs are cheap "entry-watch"** (catch a name dipping
into a buy zone) and only the bookend runs do full enrichment. Must stay well under API limits
and not waste subscription tokens.

## A. Run modes (one routine, branch by ET clock)
`tracker.run --mode {preopen|intraday|postclose}`, plus an `auto` that picks by **ET** time:
- `< 9:30 ET` → **preopen** (full): forward brief.
- `09:30–15:59 ET` → **intraday** (light): entry-watch only.
- `>= 16:00 ET` → **postclose** (full): recap + earnings.
- **Non-trading day (weekend/holiday)** → no-op with a clear log (use `pandas_market_calendars`,
  not just cron's `1-5`, so market holidays are skipped). Cron is evaluated in machine-local
  time (= ET here), but the code recomputes mode in ET explicitly so it's location-proof.

## B. Cadence-aware caching (the core; correctness-sensitive)
A small **`api_cache`** table in Neon: `(cache_key TEXT PK, payload JSONB, fetched_at TIMESTAMPTZ)`.
Helper `cached(key, ttl, fetch_fn)`: return payload if **fresh**, else fetch + store.
**TTL semantics = "same ET trading day," not rolling-24h** — so the first run of a trading day
refetches daily data and later same-day runs reuse it. Per data type:

| Data | Cadence / TTL | Source |
|---|---|---|
| Fundamentals, scores, earnings-reactions | already cached (equity-cache, freshness-checked) / Neon own-fetch | `cache_source` → own fetch |
| **Earnings calendar** | **once per trading day** (new) | Finnhub |
| **Analyst recommendations** | **once per trading day** (new) | Finnhub |
| News | full runs only; intraday only for *triggered* names | Finnhub |
| Prices / technicals | every run (free) | yfinance |

This is what makes intraday cheap: a light run fetches **only prices (free)** + reads cached
slow data → ~0 metered calls unless a trigger fires.

## C. Intraday entry-watch (light runs)
A light run: refresh prices → recompute cheap quant → check each name against **entry triggers**,
escalate (fetch news + write a short note/alert) **only** for triggered names. Triggers:
- lean ∈ {pile_on, hold} **and** thesis intact, **and** price within ~2% of support OR ≤ the
  50-day MA OR RSI cooled into a buy band → *entry-zone*.
- held name **down ≥5% on the day with thesis intact** → *notable dip*.
- **Never** on up moves / overbought. **Dedup: once per (ticker, trigger) per ET day** via an
  `intraday_alerts(ticker, trigger, alert_date)` table.

### ⚠️ Critical correctness decision — intraday must NOT wipe the narrative
Today `tracker.run` writes a fresh snapshot with **null** narrative (the routine refills it).
That's correct for full runs, but an intraday light run must **carry forward the most recent
full snapshot's narrative** (takeaway/sentiment/catalyst/final_lean/rationale/entry_guidance/
invalidation) and only update prices/quant/triggers — otherwise the app would flip to a dry,
narration-less board mid-day. So: intraday `write_snapshot` reads the latest snapshot's
narrative fields and merges them onto the fresh quant, overwriting narrative **only** for names
that triggered (which the routine then re-narrates). New field `mode` already on snapshots.

## D. Single-routine consolidation
- Delete `watchlist-preopen` + `watchlist-postclose`; create one **`watchlist`** task (frees a slot).
- Cron (one expression, shared minute): **`5 9,13,16 * * 1-5`** → 9:05 / 1:05 / 4:05 ET (recommended),
  or `5 9,12,14,16` for 4 fires.
- The prompt branches by ET time: full brief / light entry-watch / full recap (carrying §C narrative rule).

## E. Budget verification (prove we're correct, not just assume)
Instrument the pipeline with a per-run **call counter** (Finnhub/FMP/yfinance) logged at the end,
and capture token usage from the routine run. A test asserts a **light intraday run makes 0
Finnhub calls when nothing triggers** (only free yfinance). Report measured calls + tokens per
mode after the first real runs, vs the 60/min Finnhub limit.

## F. Correctness call-outs (the traps)
1. **Timezone:** all mode/TTL/day logic in **ET** (`America/New_York`), explicit — never naive local.
2. **Trading calendar:** skip holidays (calendar check), not just weekdays.
3. **Narrative preservation on intraday** (§C) — the highest-risk item.
4. **Cache TTL = per-ET-trading-day** (not 24h), so same-day runs reuse; first run of a new day refetches.
5. **Rate limits:** light runs ~0 metered; back off on 429 (already in `sources`); equity refresh
   (5:30 PM) doesn't overlap daytime watchlist runs on the shared Finnhub key.
6. **Dedup state** must be idempotent (alert once/day even if a run repeats or partially fails).
7. **Partial failure:** a failed fetch degrades to cached/None, never crashes or corrupts the snapshot.
8. **Don't double-cache:** equity-cache (slow) → `api_cache` (own-fetch slow) → live (prices) — one owner per datum.

## G. Phases (TDD, each gated)
1. **api_cache + `cached()` helper** + per-ET-day TTL. Gate: TTL hit/miss + day-boundary tests.
2. **Wire earnings-calendar + analyst through the cache** (daily). Gate: 2nd same-day call makes 0 API calls (counter test).
3. **Mode = auto** (ET clock + trading-calendar no-op). Gate: time→mode table; holiday no-op.
4. **Intraday snapshot write preserves narrative** (§C). Gate: light run keeps prior takeaways; re-narrates only triggers.
5. **Entry-watch triggers + dedup**. Gate: each trigger fires/not on synthetic data; up-move/overbought never fire; once-per-day.
6. **Call-counter instrumentation + budget test**. Gate: light run = 0 Finnhub when no trigger.
7. **Consolidate routines → one** clock-branched task; update `ROUTINE.md`.
8. **e2e**: run all three modes against Neon; confirm app stays enriched intraday; measure real budget.

## H. Open decision
- Cadence: **3 fires (9:05/1:05/4:05)** [recommended] vs 4 (`9/12/14/16`). Default 3 unless you say otherwise.
