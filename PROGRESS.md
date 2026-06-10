# PROGRESS — tickers_watchlist

> Session-spanning log so a future session knows exactly what exists, why, and what's next.
> Map docs: `README.md` (overview), `ROUTINE.md` (scheduled routine + narrative style rules),
> `docs/PLAN-v2.md` (v2 design + test plan), `docs/PLAN-fundamentals-freshness.md` (quarterly
> backfill + freshness gate), `docs/architecture.html` (educational walkthrough). This file = status + roadmap.

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
- **Current book:** 22 tickers (incl. HIMS 35.22603sh added 6/5, NOW 8.63537sh, COHR, CRDO, LITE; rest ~$200 each).

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

## Latest session (2026-06-10) — v3 accuracy fixes, branch `v3-accuracy-fixes` (NOT yet merged)

Full external-quality review of the codebase + methodology → `docs/PLAN-v3-accuracy-fixes.md`
(plan itself reviewed by 2 independent agents, revised, decisions D1–D4 resolved with the user),
then implemented in 12 gated TDD phases (P0–P10). **266 tests pass** (was 143), plus 10
integration tests run green against local Docker PG. Highlights:

- **P0 guard rails:** runtime cache-isolation proof (equity-research repo NEVER touched —
  hard user constraint), golden-snapshot diff harness (each phase may only change declared
  keys), characterization baselines, pre-v3 compat fixture (Python + typed TS).
- **P1 ledger fix (the must-fix):** `current_positions` avg cost was all-time-buys math —
  wrong after any sell-then-rebuy; replaced with a chronological recursive-CTE fold
  (migration 0006), SQL == Python reference on an 8-scenario matrix, integration-gated.
- **P2:** `watch` on held names (live bug, 4 names) coerced to `hold` with visible
  provenance; validation in both pipeline + enrich; ROUTINE.md contract updated.
- **P3 (D3):** RS deterioration = Mansfield/Weinstein regime (RS line vs its 50-session MA),
  replacing any-magnitude rs20d<0 (HIMS −0.77pp false flag).
- **P4:** mild margin-QoQ flags need margin-YoY ≤0 corroboration (seasonality); severe
  (≤−5pp) unconditional; margin_severe exposed; migration 0007; own-fetch path covered.
- **P4b (D2):** hard/soft confluence — trim needs ≥1 hard dimension; soft+soft → hold +
  Review badge (today's 4 trim proposals were all soft+soft). Config-tunable, provisional.
- **P5:** Finnhub calendar failure ≠ "no earnings" (None never cached); confirmed dates beat
  yfinance estimates (`next_date_estimated` flag); t7/t1 alerts in-window not exact-day;
  preopen big_move suppressed (movers chart now derives from day_change_pct).
- **P6:** returns + RS on dividend-adjusted closes (total return); technicals stay raw.
- **P7 (D1):** TTM honesty — all 3 display sites label TTM as TTM; rules prefer guarded
  single-quarter YoY (`*_yoy_q`); post-earnings TTM gate via read-only `get_fmp_refreshed_at`.
- **P8:** `narrative_as_of` + tri-state freshness per ticker; `data_health` block (fetch
  failures visible); web staleness chips + failure banner.
- **P9:** RSI band 30 (resolved v2 decision), dead config keys removed, Wilder ATR.
- **P10 (D4):** `python -m tracker.backtest` (no-lookahead, refuses conclusions under n=30)
  + sleeve TWR vs SPY/QQQ + max drawdown (time-weighted — contributions aren't returns),
  board scoreboard row.

**Merge ops (after review):** `python -m tracker.migrate` on Neon (0006 view swap + 0007
column), re-run `python -m tracker.backfill_fundamentals --verify` (populates margin YoY),
`vercel deploy --prod --cwd web`. Next: 2 independent diff reviews → user localhost review.

## Previous session (2026-06-05) — SHIPPED & LIVE on `main`

**New features (commit `2aaf7f9`, deployed to prod):**
- **Analyst price-target range strip** (`web/src/components/TargetRange.tsx`, on the ticker page under
  "What analysts think") — horizontal low→high bar with median + mean ticks, a current-price marker, and
  upside-to-consensus % + skew. Data: `tracker/price_targets.py` (yfinance low/median/mean/high + #analysts,
  US + ADRs), wired into `snapshot.build_ticker_row` as `price_target` (cached per ET day), typed in
  `types.ts`. **Deliberately NOT a true boxplot:** per-analyst raw targets (needed for real quartiles/outliers)
  are 402/404 on our FMP tier, so we draw only real numbers — no invented percentiles. `tracker/backfill_targets.py`
  patches the field into the current snapshot so it shows now; every future run populates it natively.
- **Live-priced book value** (money only) — `web/src/lib/quotes.ts` fetches Finnhub `/quote` (one cached-60s
  call per name, US+ADR; FMP quote is rate-limited/402). `getLivePositions(snap, livePrices)` now prices
  book/P&L/position values with the live quote when present, else snapshot (never a broken number on failure).
  Home page shows a green **"live · HH:MM ET"** tag; the per-ticker quote and ALL narrative stay at the
  snapshot timestamp so words never contradict the price. Needs **`FINNHUB_API_KEY`** (added to Vercel
  prod/preview/dev). Verified live: $22,235 live vs $22,337 snapshot, all 22 names priced.

**Follow-up fixes (commit `000da89`, deployed `dpl_8ViSBUbabj8…`):**
- **Returns in narrative prose now color** — `RichText.tsx` colored only signed (+/−) numbers, but the
  routine writes returns as words ("down 11.3%", "up 7%"), which fell through to plain bold. Added a
  `directionBefore()` check that colors a figure red ▼ / green ▲ when the preceding word is directional;
  neutral levels (172k, $464, "near 10%") stay bold.
- **"as of" timestamp was UTC** — server-rendered on Vercel (UTC clock) with no `timeZone`, so a 1:15 PM ET
  snapshot printed "5:15 PM" and looked stale/future-dated. Pinned to `America/New_York` + `timeZoneName`
  on `page.tsx` and `ticker/[symbol]/page.tsx`.
- **Book-value total now updates after a trade** — trades posted via a Route Handler (`fetch /api/transactions`)
  only revalidated the current route, so the board's "Your book" total lagged the per-ticker share count
  (ticker page updated, board didn't). Replaced with a **Server Action** `recordTrade()` in
  `web/src/app/actions.ts` that calls `revalidatePath("/","layout")`, so every page refreshes on next nav.
  `PositionEditor.tsx` now calls the action. (The `/api/transactions` Route Handler still exists for GET.)
  Book value is otherwise priced at the **last snapshot price** (not a live quote on load) — math verified
  correct ($22,337 = ledger shares × 1:15 PM prices vs $23,763 invested). Live-on-load pricing was offered
  and **not** taken (user's issue was shares, not price).

Merged to `main` (commits `befff5c` web + `ea9e4a3` pipeline) and **deployed to Vercel prod**
via `vercel deploy --prod --cwd web` (deploy `dpl_J8Jgup…`). NOTE: **this project does NOT auto-deploy
on git push** — prod deploys are manual (CLI/MCP). **136 tests pass.** The fundamentals work was
reviewed by 2 independent agents; their findings (uncovered-path gate + EPS guard) are fixed.

**Web (phone app) — new files/behaviour:**
- **Tabbed nav** (`web/src/components/TabBar.tsx`, in `layout.tsx`): Watchlist / Tickers / Methodology.
- **Tickers tab** (`ticker/[symbol]/page.tsx` + `TickerNav.tsx`): dropdown + ‹ › arrows + left/right
  **swipe** to switch names; `ticker/page.tsx` index redirects to the first held name; order in
  `lib/order.ts`. **Position-first** layout via `PositionPanel.tsx` (Trim/add button beside the header).
- **Decision matrix** (`DecisionMatrix.tsx`, "Why this call"): each metric placed on the
  Exit/Trim/Hold/Pile-on axis + the rule's Decision dot + a plain-English tally note. Faithful to the
  rule engine, no invented scores. (Chosen after exploring waterfall/gauge — see `docs/decision-visual-mock.html`.)
- **Readability:** `RichText.tsx` (signed numbers colored + ▲/▼, $ and magnitudes bold, tickers bold);
  color-bar `SectionHeader`; deleted helper subtitles; lean-colored action word; "as of" timestamps;
  hidden-empty fundamental tiles; methodology metric colors.
- **Narrative style rule:** NO em-dashes, NO color words (GREEN/RED) — baked into `ROUTINE.md` + the
  scheduled task prompt; `RichText` also strips em-dashes at render.

**Pipeline — quarterly fundamentals + earnings-aware freshness gate (the big one):**
- `tracker/quarterly.py`: pure math — Rev QoQ, gross margin, margin QoQ (pp), **guarded** YoY (None on
  non-positive/near-zero year-ago denominator), the yfinance `quarterly_income_stmt` parser, and `is_stale`.
- `tracker/store.get_fundamentals(ticker, earnings=…)`: freshness gate on BOTH paths. Fills ONLY
  `revenue_qoq_pct` + `gross_margin_qoq_pp` into the cache result (never overwrites cache TTM); if a newer
  quarter was reported (last_date > report_date + 100d) but the statement isn't in yfinance yet, returns
  those as **None (insufficient)**, never a stale quarter; refetches only on a real quarter advance (no
  thrash); 45-day confirm backstop. Helpers `_fresh_quarterly`, `_apply_quarterly`, `_is_behind`.
- `tracker/fundamentals.py`: EPS YoY guarded. `tracker/cache_source.py`: EPS growth falls back to
  `earnings_growth_ttm`. `tracker/snapshot.build_ticker_row`: computes `earn` before fundamentals, passes it.
- `tracker/backfill_fundamentals.py`: one-time/re-runnable populate of the `fundamentals` table for
  cache-covered names — `python -m tracker.backfill_fundamentals --verify`. **Already run once** (data in Neon).
- Tests: `test_quarterly.py`, `test_quarterly_fetch.py`, `test_fundamentals_freshness.py`,
  `test_fundamentals_merge.py` (incl. the "fill QoQ, preserve TTM" invariant).

**IMPORTANT — what fills WHEN:** the backfill populated Neon's `fundamentals` table and the gate is live
in code, but the **app's snapshot won't show Rev QoQ / the fully-populated matrix until the next full
pipeline run regenerates the snapshot** (4:14 ET post-close, which also re-narrates so prices+words stay
in sync — don't force a mid-day run). Names that reported very recently (yfinance statement lag, e.g.
AVGO/CRDO/CRWD as of 6/5) correctly show Rev QoQ as "insufficient" until yfinance publishes.

**Freshness audit (done 6/5):** all live inputs current — prices/technicals per run; cache TTM 20h (≤36h
window) and already reflects June earnings; QoQ earnings-gated; analyst/earnings per ET-day. Residual:
the **cache TTM growth** (revenue/EPS YoY) is NOT hard-gated — it relies on the sister daily refresh +
36h window, so ~≤36h post-earnings lag is possible (offered to extend the gate to TTM; not yet done).

**Branch state:** merged feature branches deleted LOCALLY; the 3 remote branches
(`docs/architecture-page`, `fix/snapshot-nan-guard`, `feature/tabs-nav-and-readability`) **kept on GitHub**
at the user's request (delete later). `.claude/launch.json` = local preview-server config (uncommitted; ignore).

**Docs added:** `docs/architecture.html` (educational walkthrough, on `main`), `docs/PLAN-fundamentals-freshness.md`
(freshness plan + test gates), `docs/decision-visual-mock.html` (decision-viz exploration).

## Known tradeoffs / open items
- **TTM vs QoQ:** RESOLVED (6/5) — Rev QoQ + margin QoQ are now backfilled from yfinance quarterly and
  earnings-gated, so the thesis-break flags (revenue rolling over, margin compression) can fire for all
  names. Residual: the cache's **TTM growth** (revenue/EPS YoY) is NOT hard-gated (relies on the sister
  daily refresh + a 36h window → ≤36h post-earnings lag possible). Extend the gate to TTM if desired.
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
- ~~Merge v2 → main + redeploy~~ DONE. ~~QoQ thesis flags for cache-covered names~~ DONE (6/5 backfill+gate).
1. **Extend the freshness gate to the cache TTM growth** (revenue/EPS YoY) — the one residual staleness
   window (~≤36h post-earnings); flag YoY as "updating" when last_date is newer than the cache vintage.
2. **Backtesting** — replay stored `snapshots` to evaluate the decision engine: did pile_on/trim/exit
   calls precede good/bad forward returns? Tune thresholds against history.
3. **Portfolio-history charts** (every snapshot is stored — book value / position over time).
4. **Push/email alerts** for the intraday entry signals (delivery is currently the task notification).
5. **Sector-relative strength** (vs sector ETF, not just SPY).
6. **Delete the 3 merged remote branches** + the old disabled `watchlist-preopen`/`-postclose` scheduled
   tasks (UI delete frees slots). 7. Consider a paid FMP tier OR fuller reliance on the equity cache + Finnhub.
8. **Deploys are manual:** `vercel deploy --prod --cwd web` (no git auto-deploy on this project).

## Run / resume
```bash
cd ~/tickers_watchlist && source .venv/bin/activate
python -m tracker.migrate && python -m tracker.seed      # one-time DB setup
python -m tracker.backfill_fundamentals --verify         # populate quarterly QoQ/margin (free, re-runnable)
python -m tracker.run --mode postclose                   # pipeline → snapshot → Neon (qoq + freshness gate)
python -m tracker.enrich                                  # merge out/enrichment.json → Neon
python -m tracker.append_ticker HIMS                      # add ONE ticker without a full refresh
python -m pytest tests/ -q                                # 136 tests
cd web && npm run dev                                     # local app (reads Neon)
vercel deploy --prod --cwd web                            # MANUAL prod deploy (no git auto-deploy)
```
