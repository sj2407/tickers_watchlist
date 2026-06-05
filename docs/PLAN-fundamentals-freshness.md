# Plan — quarterly fundamentals backfill + freshness guarantee

Goal: fill the missing quarterly fundamentals (**Rev QoQ**, **margin QoQ**; YoY only for the
non-cache names) **and guarantee the live decision never runs on stale earnings.** Two independent
agent reviews flagged the staleness traps; this plan encodes the fixes with tests at every step.

## Principles (from the reviews)
1. **Freshness gate lives inside `store.get_fundamentals`** — source-agnostic, runs on every mode
   (the cache short-circuit and the light intraday run must not bypass it).
2. **Compare like-to-like dates.** Never compare an earnings *announcement* date to a fiscal
   *period-end*. We compare the announcement date to *when we fetched*, and we compare *fiscal
   periods* to *fiscal periods*.
3. **Degrade, don't assert.** When a report has landed but the new statement isn't available yet
   (yfinance/FMP lag), the QoQ/margin fields return **insufficient (null)** — the engine shows no
   signal rather than last quarter's. Never thrash: refetch at most once per run, bump `fetched_at`
   only when the quarter actually advances.
4. **Keep YoY from the cache (TTM).** Backfill only the robust QoQ ratios for cache-covered names.
   Single-quarter EPS YoY is fragile (negative/zero denominator flips the sign) and `eps_yoy < 0`
   triggers a trim, so any computed YoY emits **null** when the year-ago EPS ≤ 0 or |EPS| < 0.02.
5. **Double freshness check (cross-source).** Don't trust one feed's freshness. Independently
   confirm the latest *reported* quarter from a second signal and refuse to use anything older.

## The double freshness check
We already pull earnings dates from **two** sources (Finnhub calendar + yfinance `get_earnings_dates`).
The check layers three guards, cheapest first:

- **Guard A (per run, free): announcement vs fetch time.** If `earnings.last_date` (most recent
  reported date, max of Finnhub + yfinance) is on/after the day we last fetched the ticker's
  fundamentals (`fetched_at`), a report landed after our pull → refetch.
- **Guard B (per run, free): fiscal-period agreement.** Map `earnings.last_date` to the fiscal
  quarter it reports, and compare to the stored `report_date`'s quarter. If the latest reported
  quarter is newer than what we hold → the QoQ/margin fields are marked **insufficient** until a
  refetch advances them. (Handles the yfinance-lag window safely.)
- **Guard C (periodic / verification, paid-ish): online confirmation.** A weekly audit (and a
  one-time check right after the backfill) independently looks up each held name's latest earnings
  date (Finnhub `earnings` endpoint, with a `WebSearch` fallback) and asserts our stored
  `report_date` corresponds to it. Mismatches are logged and the affected fields degrade to
  insufficient. This is the "check online" backstop — not run every minute (cost), but enough to
  catch a feed silently lagging.

## Schema (no new table; one nullable column)
`fundamentals` already has `report_date, revenue_qoq_pct, gross_margin_qoq_pp, eps_yoy, fetched_at, source`.
Add (migration 0006): `announced_date date NULL` and `quarter_basis text NULL` (e.g. "2026Q1") so the
freshness check compares fiscal periods, not raw dates. Additive, backward-compatible.

## Phases (each ships only when its tests pass; the existing 103 tests stay green)

### Phase 1 — Pure quarterly math (`tracker/quarterly.py`), no network
Functions over a list of `{period_end, revenue, eps, gross_profit}` (newest-first, validated):
`rev_qoq`, `gross_margin`, `gross_margin_qoq_pp`, `yoy_guarded`.
**Tests (`tests/test_quarterly.py`):**
- rev_qoq = (Q0/Q1−1)×100; needs ≥2 quarters else None.
- gross_margin_qoq_pp computed in **percentage points** from percent margins (49.9 − 49.0 = 0.9, not 0.009).
- yoy_guarded: Q4 ≤ 0 or |Q4| < 0.02 → **None** (no bogus %); normal case correct; needs ≥5 quarters.
- swing-to-loss (HIMS: +0.20 → −0.40) → returns a **negative** signal or None, never a positive.
- unsorted columns → sorted newest-first; NaN cells → None; missing EPS row → eps None.

### Phase 2 — Fetch adapter (`tracker/quarterly.fetch_quarters`)
Wraps yfinance `quarterly_income_stmt` (FMP `/stable` quarterly as fallback for US): returns the
validated quarters list + `latest_period_end`. NaN→None, requires ≥2 cols, skips semiannual/short
ADR histories.
**Tests:** feed a fixture DataFrame (AMAT-like) → expected quarters; missing rows / NaN / 1-column → graceful None.

### Phase 3 — Storage + fill-null merge in `store.get_fundamentals`
Upsert computed fields (+ `report_date`, `announced_date`, `quarter_basis`, `source="yfinance-backfill"`,
`fetched_at`). After a cache hit, **fill only nulls** for `revenue_qoq_pct`, `gross_margin_qoq_pp`
(and `eps_yoy` only for non-cache names) — never overwrite cache TTM.
**Tests (`tests/test_fundamentals_merge.py`):**
- merge fills a null QoQ from the Neon row; does NOT overwrite a present cache `revenue_yoy`.
- uncovered name → backfilled values used directly.
- upsert tolerates partial dicts; unknown keys ignored (no SQL error).

### Phase 4 — Freshness gate (Guards A & B) inside `get_fundamentals`
`get_fundamentals(ticker, earnings=None)` — when earnings is passed, apply the gate; refetch or mark
insufficient per the rules; bump `fetched_at` only on quarter-advance; one refetch per call.
**Tests (`tests/test_fundamentals_freshness.py`):**
- last_date ≥ fetched_at → refetch attempted.
- refetch advances quarter → values fresh, fetched_at bumped.
- refetch does NOT advance + last_date within ~10d → QoQ/margin = **None (insufficient)**, fetched_at NOT bumped.
- fiscal-period mismatch (latest reported quarter newer than stored) → insufficient.
- refetch fails (returns None) → stale row NOT served as fresh; stays flagged for next run.
- no last_date → falls back to time backstop (refetch if fetched_at older than N days), never asserts fresh.

### Phase 5 — Wire into the pipeline
`build_ticker_row` computes `earn` first, passes `earnings` into `get_fundamentals`. Snapshot carries
`fundamentals.report_date` + an `as_of`/`stale` marker. Runs on every mode.
**Tests:** snapshot row exposes report_date; an insufficient flag hides/greys the affected tiles + the
thesis flag returns None (no false trim).

### Phase 6 — One-time backfill + online verification (Guard C)
`python -m tracker.backfill_fundamentals` populates all names. Then a verification pass cross-checks
each held name's latest earnings date online (Finnhub `earnings`, WebSearch fallback) against the
stored `report_date`/`quarter_basis`.
**Checks (manual + a `tests/test_freshness_audit.py` smoke test on fixtures):**
- every held name has rev_qoq + margin_qoq with a report_date.
- spot-verify 3 names' latest quarter vs their actual last report (e.g. AMAT 2026Q1 rev $7.91B, EPS $3.51).
- the online cross-check agrees with the stored quarter for all held names (log any drift).

### Phase 7 — UI + cadence
Show the fundamentals `report_date` ("Fundamentals as of Q__ ") on the ticker page; insufficient →
tile hidden. Schedule: backfill/refresh runs targeted inside each full pipeline run (Guards A/B free);
the online audit (Guard C) runs weekly + once after the initial backfill.

## Rollback / safety
- All additive: fills nulls, never overwrites cache TTM; a failed fetch leaves the prior value but
  flagged, never asserted-fresh.
- If anything misbehaves, the fields simply return to "insufficient" (the pre-backfill state) — the
  decision engine already treats null fundamentals as "no signal", so it degrades safely.
