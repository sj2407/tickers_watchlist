# v3 Plan — accuracy fixes + methodology hardening (from the 2026-06-10 full review)

**Status:** PLAN, revised after **2 independent agent reviews of the plan itself**
(Reviewer 1: correctness/completeness → "sound-with-changes"; Reviewer 2: test
adequacy/surgical-ness → "adequate-with-changes"). All review findings are folded in
below; §11 logs what changed. Workflow: this plan → user approval → phased TDD
implementation → 2 independent reviews of the diff → user review → merge + manual deploy.

---

## 0. Hard constraints (apply to every phase)

1. **ZERO impact on `~/equity-research-agent`.** That repo is read-only input
   (`tracker/cache_source.py`, SQLite opened `mode=ro`). No phase writes to it, changes
   its schema, or alters how it refreshes. New metrics are computed *on top*, stored only
   in this repo's Neon/snapshot. Enforced by a **runtime** guard test (P0), not a grep.
   If any future phase would need to touch that project, STOP and ask the user — none in
   this plan does. (The one P7 nuance: a new *public accessor* for the cache's
   `fmp_refreshed_at` meta timestamp is added in **this repo's** `cache_source.py`,
   read-only — flagged per the user's "tell me ahead of time" rule; it reads, never writes.)
2. **Surgical = provable.** Tests FIRST (red), then the fix (green). Phase gate:
   (a) new tests pass; (b) the FULL suite passes **byte-identical except edits explicitly
   listed in that phase** — any other test edit is a stop-and-report; (c) the P0
   golden-snapshot diff shows changes ONLY in that phase's declared keys; (d) web-touching
   phases also gate on `tsc --noEmit` + `next build`.
3. **Backward compatibility:** the app renders any previously stored snapshot (all new
   fields optional; absent = degrade gracefully). P0 ships a typed fixture compiled under
   `tsc` to prove optionality, not just "doesn't crash."
4. **All names are held** (~$200 minimum = a real position, kept deliberately for
   monitoring stake). `watch` becomes an internal edge case (zero shares only), never a
   routine-written lean for a held name (P2).
5. Migrations forward-only (`0006+`), standard Postgres, Neon-safe, no extensions.

---

## P0 — guard rails (write before anything else)

1. **Cache isolation (runtime, not grep):** `tests/test_cache_isolation.py` builds a temp
   SQLite cache fixture, sha256s the file, calls all three public getters
   (+ the new P7 accessor once it exists), asserts the file hash is unchanged AND — via a
   monkeypatched `sqlite3.connect` recorder — that every connect URI contains `mode=ro`.
   Plus a repo-wide grep test: `EQUITY_CACHE_DB`/`CACHE_DB` referenced only in
   `cache_source.py` and tests.
2. **Golden-snapshot harness (the cross-phase safety net):**
   `tests/test_golden_snapshot.py` — monkeypatch all of `sources.*` with deterministic
   synthetic data, `db.using_db → False`, cache disabled, run `build_snapshot("postclose")`
   (and one `"intraday"`), normalize volatile keys (`generated_at`), diff against a
   checked-in golden JSON. **Each phase may update only its declared keys** (the diff is
   reviewed, not regenerated blindly). This is the only net that catches regressions in
   the currently-untested assembly path (`build_ticker_row`, `_next_earnings`,
   `_portfolio_block`, `_mechanical_alerts`, intraday lean-seeding, `_price_series`).
3. **Characterization tests for currently-uncovered code that later phases touch**
   (red-proof: they pass today, pinning today's behavior):
   - `tests/test_returns_characterization.py`: calendar-anchored r1/5/20d + positional
     fallback on a synthetic frame; `relative_strength` values. (Consumed by P6.)
   - `tests/test_next_earnings.py`: past/upcoming date selection, actuals mapping,
     `last_eps_surprise_pct`. (Consumed by P5.)
   - badge characterization in `tests/test_badges.py`: revenue badge text/tone for
     +20 / −5 / None. (Consumed by P7.)
4. **Snapshot-compat:** pre-v3 fixture (trimmed from today's real snapshot) through
   `merge_narrative` + `build_signals` + `triggers.compute_triggers` with **concrete
   value assertions** (carried fields equal fixture values), plus a `const s: Snapshot =
   fixture` typed file under the `tsc` gate.

**Gate:** suite green; these tests never change again in this plan (except declared
golden-diff updates).

---

## P1 — position ledger: correct average-cost math (the must-fix)

**Bug:** `current_positions` (migrations/0001) computes `avg_cost = all-time buy cost /
all-time buy shares`. Average-cost requires a chronological fold: buys re-average over
(remaining + new) shares; sells leave avg unchanged and realize P/L at the avg *at sale
time*; a closed position resets. Current view misprices avg/invested/unrealized/
since-entry and computes realized P/L retroactively.

**Fix:** migration `0006_position_avg_cost.sql` replacing the view with a recursive-CTE
fold over `transactions` ordered `(executed_at, id)` per ticker. **Exact fold spec**
(amended per review — NULL/zero-share edges):

- `matched = LEAST(sell_shares, shares_held)`
- buy: `shares += s`; `cost += s·p + fees`; sell: `realized += CASE WHEN matched > 0
  THEN matched·(p − avg) ELSE 0 END − fees` (fees on a fully-clamped oversell still
  subtract — they're real costs); `shares −= matched`; `cost = shares·avg`
- `avg = CASE WHEN shares > 0 THEN cost/shares END` (NULL at zero shares — never a
  divide-by-zero, and NULL never propagates into `realized`, which is COALESCE-guarded)
- shares hits 0 → `cost = 0`; next buy re-seeds avg fresh.
- Output columns **identical**: `(ticker, shares, avg_cost, invested, realized_pl)` —
  the only two readers (`tracker/db.py:fetch_positions`, `web/src/lib/data.ts:
  getCurrentPositions`) need no changes; an information_schema assertion pins this.

**Pre-set tests (`tests/test_positions_view.py` + `tracker/positions.py` reference):**
- Python reference fold, scenario matrix: buy-only · buy/partial-sell · sell-then-rebuy
  (10@100, sell 5@150, buy 5@200 → shares 10, avg **150.00**, invested 1500, realized
  250) · full-exit-then-rebuy (avg **200**, realized 500) · fees both sides ·
  **sell-before-any-buy** (realized = −fees, shares 0, avg NULL) · oversell clamp ·
  same-timestamp id ordering.
- Integration (`@pytest.mark.integration`, against the local `wl-pg` Docker PG via
  `TEST_DATABASE_URL`): apply migrations to a throwaway schema, run every scenario,
  assert SQL view == Python reference row-for-row.
- **Merge gate (amended per review — no silent skip):** P1 may not merge unless the
  integration tests **actually ran**: `pytest -m integration -ra` with collected > 0 and
  0 skipped; a sentinel test fails if `TEST_DATABASE_URL` is set but no scenario ran.

**Existing tests allowed to change:** none. **Ops:** `python -m tracker.migrate` on Neon;
it's a view — no data rewrite, reversible.

---

## P2 — lean vocabulary: never `watch` on a held name

**Bug (live):** routine wrote `final_lean="watch"` for 4 held names (2 hiding quant trim
proposals). Nothing validates routine output.

**Fix:**
1. `tracker/enrich.py` validates **all merged snapshot rows post-merge** (amended per
   review — not just the overlay tickers, so carried-forward bad leans heal too, without
   waiting on the LLM): held + `watch` → coerce to `hold`, set
   `lean_coerced_from="watch"`; held + value outside `{pile_on,hold,trim,exit}` → keep
   prior/provisional, set `lean_rejected=<value>`; non-held + anything outside
   `{watch,hold}` → coerce to `watch` + flag. `lean_coerced_from` is added to
   `NARRATIVE_TICKER_FIELDS` so the visibility flag survives carry-forward with the lean
   it explains.
2. `ROUTINE.md`: every tracked name is held; `watch` invalid for held names; the LLM may
   not demote a quant `trim` to a non-action label without addressing it in the rationale.

**Pre-set tests (`tests/test_enrich_validation.py`):** watch-on-held → hold + flag;
junk-on-held → rejected + prior kept; valid leans untouched; non-held watch preserved;
non-held junk → watch + flag; **carried-forward** watch-on-held (not in overlay) also
coerced; coercion flag survives `merge_narrative`; **trigger-eligibility change pinned**
(per review: a held name frozen by `watch` becomes entry-eligible after coercion —
intended, now asserted in `test_triggers.py`); tests stub `store.publish_enriched` and
use `tmp_path` (no side effects).
**Existing tests allowed to change:** none. Today's 4 bad leans heal at the first
post-P2 enrich run (validation is post-merge, not LLM-dependent).

---

## P3 — relative-strength deterioration: the industry-standard regime test (D3 resolved)

**Bug:** `signals.py:191` counts `rs20d < 0` of any magnitude as a deterioration
dimension (HIMS flagged at −0.77pp). PLAN-v2 §4 says "sustained."

**D3 resolution (user asked for the industry standard):** the established practice
(Stan Weinstein's Stage Analysis / Mansfield Relative Strength, also the basis of IBD's
RS-line reads) defines RS deterioration as a **regime**, not a one-period percentage:
the RS line (price ÷ benchmark) trading **below its own moving average** — 52-week MA on
weeklies in the original; daily adaptations use the ~50-session MA. Academic support for
dropping the 20-day cutoff entirely: 1-month relative returns are dominated by short-term
reversal noise (momentum literature uses 3–12 month windows), so ANY fixed −Xpp/20d
threshold is non-standard. We adopt the Mansfield-style daily regime test.

**Fix:** in `market_data.py`, compute the RS line `ticker_adj_close / bench_adj_close`
(date-aligned; adjusted closes once P6 lands — raw `Close` until then, the regime test is
ratio-based so the difference is negligible) and emit into `relative_strength`:
`rs_line_ma50_dist_pct` (ratio vs its 50-session MA, %) and
`rs_trend: "outperforming" | "underperforming" | null` (null when <51 aligned sessions).
`signals.py`: `negative_rel_strength = rs_trend == "underperforming"`. `rs20d` stays as a
display/momentum metric and keeps driving the pile side (`rs20d > 0` = "leading the
market"; `rs_ok` unchanged). New registry entry `rs_trend` (with the Mansfield/Weinstein
explanation) + `export_metrics` re-run (glossary parity). **Web:** `DecisionMatrix.tsx`
hard-codes `r20 >= 0 ? hold : trim-zone` — switch its RS row to `rs_trend` (underperforming
→ trim zone; outperforming or null → hold/pile placement) so the "Why this call" matrix
can't contradict the engine; P3 gains the `tsc`/`next build` gate.

**Pre-set tests:** synthetic steady-laggard series (ratio persistently below its 50d MA)
→ `underperforming` + counts as deterioration; **the HIMS case** — a name slightly behind
SPY for a couple of weeks but whose RS line is still at/above its 50d MA → NOT flagged;
crossover boundary (ratio crossing the MA flips the regime); <51 sessions → null →
never counts (None-safe); rs20d = −0.77 with `rs_trend=outperforming` + one other flag →
hold (pins that the old any-negative behavior is gone); rs20d −1.0 on an otherwise-strong
name → hold, not pile_on (pins the pile side).
**Existing tests allowed to change:** decision-engine fixtures that construct trims via
`rs20=-3.0` must instead set `rs_trend="underperforming"` — each edit listed; assertions
must not be weakened (the trim still requires the second dimension).

---

## P4 — margin compression: seasonality-aware

**Bug:** mild flag fires on any sequential gross-margin dip ≥2pp; seasonal mix swings
(semis/hardware) create false confluence.

**Fix:**
- `quarterly.py`: `gross_margin_yoy_pp(quarters)` (Q0 margin − Q4 margin, pp, ≥5
  quarters, None-guarded); included in `record_from_quarters`.
- **`fundamentals.compute()` computes it too** (amended per review — FMP already fetches
  8 quarters; without this, the ~4 non-cache names would silently lose the mild flag
  forever).
- Migration `0007_margin_yoy.sql`: `ALTER TABLE fundamentals ADD COLUMN IF NOT EXISTS
  gross_margin_yoy_pp double precision;` + `db._FUND_COLS`.
- `thesis.py`: **severe** QoQ ≤ −5pp flags unconditionally (unchanged); **mild** QoQ
  ≤ −2pp flags only if `gross_margin_yoy_pp ≤ 0`; YoY None → mild alone does not flag;
  hypergrowth suppression unchanged, applied after.
- `_apply_quarterly` overlays `gross_margin_yoy_pp` (fill-null, degrade-on-stale, same as
  QoQ fields). Registry text + glossary re-export. One-time
  `python -m tracker.backfill_fundamentals --verify` re-run (this repo only).

**Pre-set tests:** thesis layer — severe −6pp + YoY +3 → True; mild −2.5 + YoY −1 → True;
mild −2.5 + YoY +2 → False; mild + YoY None → no flag; **YoY exactly 0.0 → flags (≤ 0)**;
**severe exactly −5.0 + YoY positive → True** (boundaries per review); suppression
interplay. Math/guards in `test_quarterly.py`. **Store layer (amended per review — the
wiring, not just the unit):** in `tests/test_fundamentals_merge.py`:
`test_covered_fresh_fills_margin_yoy_pp` (cache dict lacks the key, quarterly row
supplies it → present in `store.get_fundamentals` output) and
`test_covered_stale_nulls_margin_yoy_pp`.
**Existing tests allowed to change:** exactly `test_flags_fire_on_deterioration`,
`test_boundaries_are_inclusive`, `test_margin_compression_fires_when_growth_is_weak`
(tests/test_thesis.py) — **by adding `gross_margin_yoy_pp ≤ 0` to fixtures so they keep
asserting True** (never by flipping expectations; per review, that would silently weaken
the original intent).

---

## P4b — trim-confluence hardness: placeholder now, tuned later (D2 resolved)

**D2 resolution:** the user wants this in NOW as a provisional rule — the backtest may
never reach statistical significance on a 22-name sleeve and must not block it.

**Fix:** classify deterioration dimensions in `signals.provisional_lean`:
**hard** = `downtrend`, `revenue_weakening`, severe margin collapse (QoQ ≤ −5pp);
**soft** = `negative_rel_strength` (rs_trend), mild margin compression,
`earnings_quality_deteriorating`. `trim` requires **≥2 dimensions including ≥1 hard**;
≥2 soft-only → `hold` with a new driver note `review: soft deterioration confluence`
(and a "Review" badge) so soft+soft is never invisible — it's surfaced, just not an
auto-trim proposal. Severity boundary (severe vs mild margin) comes from the same
`thesis.py` thresholds — no duplicated constants: `thesis_break_flags` gains a
`margin_severe: True/False/None` output so the engine never re-derives it.
Classification lives in config (`signals.hard_dimensions`) so it's tunable without code,
explicitly marked provisional pending P10 evidence. Registry/methodology text + glossary
re-export; `DecisionMatrix` tally note wording updated (it already renders per-metric
zones; only the plain-English tally string changes).

**Pre-set tests:** soft+soft (rs_trend underperforming + mild margin) → `hold` + review
driver (this is exactly today's HIMS/IONQ/MP/OUST shape — pinned as a named regression
case); hard+soft → trim; hard+hard → trim; 1 hard alone → hold (confluence still ≥2);
severe-margin classification comes from thesis output, not a re-derived threshold
(asserted); config override flips a dimension's class.
**Existing tests allowed to change:** decision-engine trim fixtures that are currently
soft+soft must add a hard dimension to keep asserting `trim` — each edit listed; the
soft+soft originals are KEPT and re-asserted as `hold`+review (no deleted coverage).

---

## P5 — earnings calendar: failure ≠ "no earnings", confirmed dates first, sane alerts

**Bugs:** (a) failed Finnhub calendar fetch returns `[]` → `api_cache` stores it for the
ET day → into-earnings guard + alerts silently off; (b) yfinance *estimated* dates union
with Finnhub's — phantom earlier date wins `next_date`; (c) t7/t1 fire only on exact
day-match, undeduped; (d) preopen `big_move` re-alerts yesterday's move.

**Fixes:**
1. `earnings_calendar` returns **None on transport failure**, `[]` only for a genuine
   empty calendar; `api_cache.cached` already skips None. `_next_earnings` treats None as
   no-data.
2. Upcoming `next_date`: **Finnhub first**; yfinance only when Finnhub returns a genuine
   empty (`[]`). **On Finnhub failure (None)** (ambiguity resolved per review): fall back
   to yfinance but set `earnings.next_date_estimated = true`, so the routine/UI can say
   "date unconfirmed" and the event guard still works. Past dates keep the union.
3. Alerts: t7 emits while `1 < days ≤ 7`, t1 while `0 ≤ days ≤ 1` — **in the snapshot on
   every run while in-window** (amended per review: the board is recomputed state, so the
   pill must not vanish from later snapshots; `claim_alert` dedup is reserved for the
   future push channel, keyed `(ticker, alert_type, next_date)` so a moved earnings date
   re-fires). File-mode == DB-mode behavior (in-window every run) — decided and pinned,
   replacing the old fire-once-on-exact-day accident.
4. `big_move` emitted only in `intraday`/`postclose`. **Web (amended per review):** the
   movers bar chart currently derives from `big_move` alerts → switch it to derive from
   `price.day_change_pct` directly, so preopen boards keep their chart while the *alert*
   disappears; P5 gains the `tsc`/`next build` gate.

**Pre-set tests (`tests/test_earnings_calendar.py` + P0's `test_next_earnings.py`
baseline):** anchored at the real storage seam (amended per review — monkeypatched
`api_cache._put`/`_get` recording dict, NOT file-mode passthrough, which proves nothing):
transport failure → None → `_put` never called → second call refetches; genuine `[]` →
`_put` once, no refetch; phantom yf date vs Finnhub confirmed → Finnhub wins; Finnhub
`[]` → yf fallback unflagged; Finnhub None → yf fallback **with** `next_date_estimated`;
t7 present at days 6 and 3 (missed-run + persistence), absent at 8 and 1; t1 at 1 and 0;
push-claim key includes the earnings date + **date-move re-fires**; preopen big_move
suppressed / intraday + postclose emitted (all three modes pinned).
**Existing tests allowed to change:** **none** (corrected per review — no current test
mocks `earnings_calendar`; the previously-listed edits referenced tests that don't exist).

---

## P6 — returns & relative strength on total-return (dividend-adjusted) closes

**Bug:** `auto_adjust=False` → `Close` is split- but not dividend-adjusted; r/rs are price
returns; SPY's quarterly ex-div (~0.3%) and holdings' ex-div days distort RS — which P3
makes a trim input.

**Fix:** `price_history` keeps `Adj Close` when yfinance provides it; `compute_returns` +
`relative_strength` prefer `Adj Close`, falling back to `Close`. **Each frame uses its own
best column independently** (mixed-frame semantics pinned per review). Technicals, charts,
S/R, book value, position math stay on raw `Close`.

**Pre-set tests (`tests/test_market_data_adjusted.py` + P0 characterization baseline):**
synthetic 1%-dividend-gap frame — adjusted r5d == hand-computed total return ≠ raw;
no-`Adj Close` frame → byte-identical to the P0 characterization values (the real
regression baseline; the old plan cited a fixture file that doesn't cover this — corrected);
**mixed frame** (ticker has Adj Close, benchmark doesn't) → each side uses its own;
`compute_technicals` identical with/without the column.
**Existing tests allowed to change:** none. **Registry note (per review):** `ret_1d`
(adjusted) and `price.day_change_pct` (quote-based) can differ on ex-div days — one
sentence added to both glossary entries.
**User-visible:** r/rs values shift by fractions of a pp vs old snapshots — expected.

---

## P7 — TTM honesty: label it everywhere, gate it, let rules prefer true YoY

**Issues:** ~18/22 names show TTM growth under a "YoY" label in **three places** (Python
badge `signals.py:121`, web `ticker/[symbol]/page.tsx` `hint="YoY"`, `DecisionMatrix.tsx`
"Revenue YoY" row — all three covered per review, not just the badge); TTM lags real
rollovers ~2 quarters; cache TTM has a ≤36h post-earnings staleness window.

**Fix (all computed on top; equity-research repo untouched):**
1. **Labels:** all three sites render "TTM" when `fundamentals.source ==
   "equity-cache(fmp,ttm)"` (source is already in the payload + types). Registry gains a
   TTM-vs-YoY explanation; glossary re-exported.
2. **Rules prefer single-quarter YoY when available (D1):** `_apply_quarterly` overlays
   `revenue_yoy_q` / `eps_yoy_q` from our quarterly table (zero new API calls,
   `yoy_guarded`), **degrading to None under the same `stale` rule as the QoQ fields**
   (pinned per review). `provisional_lean`/`build_signals` use `*_q` if present, else TTM.
   New optional fields added to `types.ts`.
3. **Post-earnings TTM gate:** new public read-only accessor
   `cache_source.get_fmp_refreshed_at()` (the meta is currently private — corrected per
   review). Semantics pinned: if `earnings.last_date ≥ today − 2d` **and**
   `fmp_refreshed_at < (last_date + 1 day, 00:00 ET)` → TTM growth fields → None
   (insufficient) for that run. Handles AMC reporters (refresh timestamp is a global
   batch stamp, date-only comparison would miss them).

**Pre-set tests:** P0 badge characterization extended per source; rule preference at
`provisional_lean` level — all four present/absent combos **including the conflict case
(TTM +20, q-YoY −5 → counts as deterioration)**; store-level coexistence test in
`test_fundamentals_merge.py` (cache TTM and q-YoY both survive the fill-null overlay);
gate pure-function tests (fresh-after-earnings kept / stale → None, AMC edge); P0 cache
isolation re-run covers the new accessor.
**Existing tests allowed to change:** **none** (corrected per review — there are no
existing badge tests; the P0 characterization test is the baseline and its declared
update is the only edit).

---

## P8 — staleness & data-health you can see

**Fix:**
1. `enrich.py` stamps `narrative_as_of` per ticker + top-level; `merge_narrative` carries
   stamps with the words.
2. **Freshness tri-state computed in Python** (amended per review — web has no test
   runner, so the logic must not live in TSX): pipeline sets per-ticker
   `narrative_freshness: "fresh" | "carried" | "stale"` (stale = >24h older than
   `generated_at`), fully unit-tested. Web renders the chip purely presentationally.
3. Snapshot `data_health`: `{finnhub_calls, finnhub_failures, tickers_missing_news,
   tickers_missing_analyst, equity_cache_used, equity_cache_age_hours}` (`sources` gains a
   failure counter beside the call counter). One-line banner when failures > 0.
   All fields optional in `types.ts` (P0 compat fixture proves old snapshots render).

**Pre-set tests:** carry-forward preserves stamp; fresh write updates it; tri-state
boundaries (24h edge) pure-function tested in Python; failure counter increments on
mocked transport errors, resets per run; `tsc` + `next build`; P0 typed fixture.
**Existing tests allowed to change:** none (golden-snapshot diff declares the new keys).

---

## P9 — hygiene: config drift + Wilder ATR

- `rsi_oversold` 35 → **30** (config.py + config.yaml; note the decision-engine test cfg
  and the web display already assume 30 — this aligns the live config with them).
- Delete dead keys `position_weight_cap_pct` + `growth_benchmark` (verified read nowhere;
  removed from **both** config.py and config.yaml).
- `_atr` → Wilder smoothing (`ewm(alpha=1/14, adjust=False)` over true range); registry
  description updated **+ glossary re-export** (added per review — `test_glossary_parity`
  fails otherwise).

**Pre-set tests:** RSI badge boundary at 30/70; ATR vs hand-computed Wilder values (none
exist today — new coverage, not an edit); config round-trip without dead keys.
**Existing tests allowed to change:** **none** (corrected per review — the previously
assumed ATR golden tests don't exist).

---

## P10 — methodology instrumentation (D4: IN SCOPE; none touch equity-research-agent)

1. **Backtest evaluator (`tracker/backtest.py`)** — replay stored Neon `snapshots`:
   forward 5d/20d returns (vs SPY) per historical lean and per deterioration dimension;
   hit-rate + excess-return report. **Evidence-builder, NOT a gate** (D2): the report
   prints sample sizes per cell and refuses to print a conclusion line under n<30 —
   honest about statistical power on a 22-name sleeve; it accumulates value as snapshots
   pile up. Read-only; CLI + markdown report. Tests on synthetic snapshot fixtures incl.
   an explicit **no-lookahead** test (a snapshot scored only with strictly-later prices).
2. **Sleeve performance block** — snapshot `performance`: book vs SPY/QQQ total-return
   since inception (stored snapshot series + adjusted benchmark closes), max drawdown,
   realized+unrealized split; small board chart. All fields optional in `types.ts`.

---

## Sequencing

P0 → P1 → P2 → P3 → P4 → P4b → P5 → P6 → P7 → P8 → P9 → P10 (each independently
shippable, full suite + golden diff green between phases; P4 before P4b — the engine
consumes thesis severity output; P4 before P7 — both extend `_apply_quarterly`; P3's
regime tests are synthetic-input so P6's return shifts can't flip them). Branch
`v3-accuracy-fixes`, one commit per phase.

## Decisions — RESOLVED (2026-06-10, with the user)

- **D1 (P7): YES** — rules prefer single-quarter YoY over TTM where available.
- **D2 (P4b): adopt NOW as a provisional, config-tunable placeholder** — do not block on
  backtest significance (22-name sleeve may never reach it). P10's backtest reports
  evidence with explicit sample-size honesty.
- **D3 (P3): use the industry standard** — Mansfield/Weinstein RS-line-below-its-MA
  regime (50-session daily adaptation), replacing any fixed −Xpp/20d cutoff.
- **D4 (P10): in scope** — backtest (non-blocking) + sleeve performance both included.

## §11 — Review round 1: amendments applied

- **R1-blocker:** P1 fold spec now handles sell-before-buy / zero-share NULL avg /
  divide-by-zero / fees-on-clamped-oversell; scenario added to the matrix.
- **R2-blocker:** P1 merge gate requires the integration suite to have actually run
  (0 skipped, sentinel test); Python-reference parity alone is insufficient.
- **R1/R2-major:** P4 extends `fundamentals.compute()` (non-cache names kept the mild
  flag) + store-level overlay tests; P7 covers all three "YoY" display sites + types +
  stale-degrade for `*_q` + public read-only `get_fmp_refreshed_at` accessor with pinned
  AMC-safe semantics; P5 alerts stay in-snapshot while in-window (dedup reserved for
  push), Finnhub-failure fallback flagged `next_date_estimated`, movers chart decoupled
  from big_move alerts, tests anchored at the storage seam; P3 fixes `DecisionMatrix`'s
  contradicting rs zone; P2 validates all merged rows post-merge and carries the
  coercion flag; P8 freshness logic moved to tested Python.
- **R2-major:** P0 gains the golden-snapshot diff harness, runtime cache-isolation guard,
  and characterization tests (returns/RS, `_next_earnings`, badges) written before the
  phases that touch them.
- **Corrections:** "existing tests allowed to change" lists for P3/P5/P7/P9 referenced
  tests that don't exist → corrected to none/explicit; P4's three real test edits named
  with a no-weakening rule; boundary cases (YoY = 0.0, severe = −5.0, rs −1.0 vs pile)
  added.
