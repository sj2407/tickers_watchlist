# Plan — intraday refreshes, cadence-aware caching, single routine (v2, post-review)

**Branch:** `v2-quant-and-glossary` · **Status:** PLAN (revised after 2 independent reviews)
**Workflow:** plan → implement (TDD, gated) → verify budget → review → merge.

> Revised to close the review findings. Key fixes baked in: a migration for `mode='intraday'`,
> `build_snapshot` becomes mode-aware (the only way the "~0 intraday calls" claim is true),
> narrative carried forward in `build_snapshot` for ALL names (never nulled), cold-start
> promotion, enrich-by-id (no cross-run clobber), app reads enriched rows only, explicit
> `trading_day` cache column, earnings-actuals same-day bypass, ET-pinned date math.

## Goal
One clock-branched routine, a few fires/day; **intraday runs are cheap entry-watch** and the
two bookend runs do full enrichment. Stay well under API limits; never wipe/clobber an output.

## A. Run modes (one routine, branch off the REAL market session)
Mode is derived from `calendar_utils.session_phase()` (already uses the XNYS schedule, so it
handles **half-days and holidays** and real open/close — not hardcoded 9:30/16:00):
- `premarket` → **preopen** (full) · `open` → **intraday** (light) · `afterhours` → **postclose** (full)
- `closed` (weekend/holiday) → **no-op**: log and exit, **touch nothing** (prior snapshot stays).
- `tracker.run --mode` accepts `{preopen,intraday,postclose,auto}`; `auto` resolves via session_phase.
- **Timezone:** all clock/day logic in `America/New_York`, explicit. **Do not assume host==ET** —
  the routine env is pinned to ET (or cron scheduled in UTC + documented). `run.py` choices updated.
- **Migration `0003`:** widen `snapshots.mode` CHECK to include `'intraday'`. Update
  `web/src/lib/types.ts` `mode` union. (Resolves the CHECK-constraint crash.)

## B. Cadence-aware caching — `api_cache` (owns ONLY earnings-calendar + analyst)
Schema: `api_cache(cache_key TEXT PK, payload JSONB, trading_day DATE NOT NULL, fetched_at TIMESTAMPTZ)`.
- **`cache_key = f"finnhub:{endpoint}:{ticker}"`** (per-ticker — non-scoped keys would collide).
- **Freshness = `row.trading_day == current_et_trading_day(now)`** (an explicit stored ET session
  date, computed via calendar_utils + ZoneInfo — NOT derived from `fetched_at` at read time).
- **Sole owner per datum (§F.8):** fundamentals stay in the existing `fundamentals` table path
  (`store.get_fundamentals`, 7-day) — **excluded from api_cache**. api_cache owns *only* the two
  genuinely-new daily fetches: **earnings calendar** + **analyst recommendations**.
- **Earnings same-day exception:** a name reporting today flips its actuals intraday, so a
  once-per-day calendar cache would serve pre-report data to the postclose run. → **Full
  (preopen/postclose) runs BYPASS the api_cache for the earnings calendar of any ticker with
  `days_until_next==0` or `last_date` within ~1 session**; intraday may reuse. Analyst recs are
  monthly-cadence → per-day cache is fine (postclose may bypass as belt-and-suspenders).
- **ET date math:** pass an explicit ET `as_of` date into `sources.company_news` /
  `sources.earnings_calendar` instead of `date.today()` (host-local), so cache keys + windows agree.

| Data | Cadence | Owner |
|---|---|---|
| Fundamentals / scores / earnings-reactions | equity-cache (freshness-checked) → Neon `fundamentals` (7d) | `cache_source` / `store` |
| **Earnings calendar** | once per ET day (bypassed on full runs for today's reporters) | `api_cache` |
| **Analyst recs** | once per ET day | `api_cache` |
| News | full runs (all); intraday only for *triggered* names | live (Finnhub) |
| Prices / technicals | every run (free) | yfinance |

## C. Snapshot write model — narrative is NEVER nulled (the core invariant)
Unify the fix in **`build_snapshot(mode)`** (it already loads `store` and knows the tickers):
1. **Carry-forward:** read the latest snapshot that actually HAS narrative (`final_lean` non-null)
   ONCE, and for EVERY ticker merge the **complete** prior enrichment onto the fresh quant:
   the 8 per-ticker fields (`takeaway, sentiment, catalyst_summary, earnings_recap, final_lean,
   rationale, entry_guidance, invalidation`) **plus top-level `market_recap` + `macro_context`**
   and the alert narrative. `build_snapshot` now emits `entry_guidance`/`invalidation` keys so
   they have a home. So **every snapshot — even pre-enrichment — already has narrative** (the
   prior run's), which also closes the publish-race (D).
2. **Intraday:** carry forward ALL names unconditionally (incl. triggered). Do **not** null a
   triggered name — instead set `intraday_triggered: [tickers]` for the routine to OVERWRITE.
   A failed/partial routine therefore leaves the prior read intact, never null.
3. **Full runs (preopen/postclose):** same carry-forward as a *floor*; the routine's enrich then
   OVERWRITES with fresh narrative for all names.
4. **Cold start:** if NO enriched snapshot exists for the current ET trading day, an `intraday`
   run **promotes to a full run** (full fetch + routine enriches) rather than publish a null board.
   If the table is entirely empty, any mode does a full fetch (enrich fills narrative).

## D. Publish ordering — enrich-by-id, app reads enriched only
- `db.insert_snapshot` **returns the new id**; `run.py` records it (working file/meta); `enrich`
  **updates THAT id** (`update_snapshot(id, payload)`), not "latest" → no cross-run clobber.
- `getLatestSnapshot` (data.ts) selects the latest row **WHERE narrative is present**
  (`payload->'tickers'->0->>'final_lean' IS NOT NULL`) → a transient/in-flight row never shows.
- Net: with (C) every insert already carries prior narrative AND (D) the app filters to enriched
  rows AND enrich targets a specific id — the race and the clobber are both closed.

## E. Budget — make the "~0 intraday calls" TRUE, then prove it
`build_snapshot(mode)` becomes **mode-aware**: in `intraday` mode it (a) **skips `company_news`
for all but triggered names**, and (b) reads analyst + earnings **only via `api_cache`** (0 calls
on a same-day repeat). yfinance prices stay (free). Instrument a per-source **call counter**
logged per run. **Gate test: a light intraday run with no triggers makes 0 Finnhub calls.**
Report measured calls + tokens per mode after first real runs vs the 60/min Finnhub limit.

## F. Correctness call-outs (now incl. review findings)
1. ET everywhere; host≠ET tolerated (pin env / UTC cron documented). Source-layer date math ET.
2. Mode + half-day/holiday via `session_phase` (real schedule), not literals.
3. **Narrative never nulled** (C) — carried for all names; routine overwrites triggered ones.
4. Cache TTL via explicit `trading_day` column; per-ticker keys.
5. Earnings actuals: full runs bypass the day-cache for today's reporters (no stale actuals).
6. Dedup: `intraday_alerts` UNIQUE`(ticker,trigger,alert_date)` + `INSERT…ON CONFLICT DO NOTHING`,
   claim-then-deliver (write the row in the same step as recording the alert; delivery tolerant).
7. Partial failure degrades to cached/None; a failed run never deletes/blanks the last good snapshot.
8. One owner per datum: fundamentals = `fundamentals` table only; api_cache = earnings-cal + analyst only.
9. No-op on closed days touches nothing (test it); long-weekend staleness is acceptable (last enriched board shows).

## G. Phases (TDD, each gated)
0. **Migration 0003** (mode CHECK += intraday) + run.py choices + types.ts. Gate: intraday row inserts/round-trips.
1. **`api_cache` + `trading_day` TTL + per-ticker keys.** Gate: same-ET-day hit / new-day miss / boundary.
2. **Route earnings-cal + analyst through api_cache; full runs bypass for today's reporters.** Gate: 2nd same-day call = 0 API; reporter bypass refetches.
3. **`mode=auto` via session_phase** (premarket/open/afterhours/closed→no-op, half-days). Gate: phase→mode table incl. half-day + holiday no-op-touches-nothing.
4. **build_snapshot carry-forward** (all names, full field set incl. market_recap/macro; emits entry_guidance/invalidation) + **cold-start promotion**. Gate: intraday keeps every prior narrative field; cold intraday promotes (no null board); non-triggered names untouched.
5. **enrich-by-id + app enriched-row filter.** Gate: enrich updates the inserted id (not newest); app never returns a null-narrative row.
6. **Entry-watch triggers + dedup.** Gate: each trigger fires/not on synthetic data; up-move/overbought never fire; once-per-(ticker,trigger,day); idempotent on retry.
7. **Mode-aware build_snapshot + call-counter.** Gate: light run, no trigger = 0 Finnhub.
8. **Consolidate 2 routines → 1** clock-branched task; update ROUTINE.md.
9. **e2e**: run all modes vs Neon; app stays enriched intraday; measure real budget.

## H. Open decision
Cadence: **3 fires 9:05/1:05/4:05 ET** [recommended] vs 4 (`9/12/14/16`). Default 3.
(Note: with §A using session_phase, 4:05 resolves as `afterhours`→postclose; on a half-day the
early close still routes correctly.)
