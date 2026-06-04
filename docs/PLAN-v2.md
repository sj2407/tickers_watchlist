# v2 Plan — richer signals, fundamentals, reworked decision engine, glossary

**Branch:** `v2-quant-and-glossary` · **Status:** PLAN (nothing implemented yet)

**Workflow:** (1) this plan → your approval → (2) implementation → (3) two independent
agent reviews of the diff → (4) you review on a localhost → (5) merge to `main` + redeploy.

This is a **consolidation, not a replacement.** Everything we built (LLM judgment,
position ledger, deployed app, twice-daily routine, narrative-first UI) stays and remains
the foundation. We pull a few well-tested *quant ingredients* from the `equity-research-agent`
`checklist-tab` branch **into** this project. One-way, additive.

---

## 1. What we're adding

| # | Addition | Source |
|---|---|---|
| A | Richer technicals: **MACD + crossover**, **golden/death cross**, **support/resistance** (swing pivots) + distance to nearest level, **breakout + volume confirmation** | port `checklist-tab/src/checklist/technicals.py` (pure functions) |
| B | **Fundamentals layer**: revenue growth YoY, EPS growth YoY, gross-margin trend, P/E vs own history | adapt (new data source + table) |
| C | **Quantified thesis-break flags**: revenue QoQ drop, margin compression, repeated EPS misses — *supporting*, not replacing, the LLM thesis-break | adapt from `checklist.py` thesis rules |
| D | **Signal provenance + `insufficient_data`** pattern: every number carries where it came from + an honest "not enough history yet" flag | adopt `checklist.py` `Signal` design |
| E | **Reworked decision engine** combining all of the above into pile / hold / trim / exit — explicitly (§4) | new |
| F | **Dictionary / Methodology tab** in the web app, driven from a single source of truth | new |

### What we deliberately DON'T port (and why)
- **Per-ticker overlay YAML system** — elegant but high manual upkeep per name; not worth it for a 21-name personal sleeve.
- **`render.py` / `server_routes.py` / the dashboard tab** — that's their UI; we have our own app.
- **The `watch/candidate/enter/hold/trim/exit` status machine** — entry-centric (for names you don't own yet); we hold everything and already have leans + LLM. See contradiction C2.
- **Their SQLite cache / Russell-3000 universe plumbing** — bound to that repo; we take ideas, not files.

---

## 2. Port vs adapt vs skip

- **Port near-verbatim:** `technicals.py` — pure functions over price/volume arrays (no DB by design), drops into our `tracker/market_data.py`. Bring its unit tests too.
- **Adapt:** fundamentals fetch + storage (their source is tied to their cache/universe; we add our own table + fetch for ~21 names); thesis-break threshold math; the `Signal` dataclass.
- **Skip:** overlays, UI/server, status machine, universe plumbing.

---

## 3. Contradictions between what we built and what we're porting — with resolutions

This is the part to scrutinize. Each clash below is real; each has an explicit resolution.

**C1 — Concentration / position size as a trim driver.** Their risk layer and the spec's
status machine trim on position size and "valuation stretched." **We deliberately removed
size as a trim driver** (small satellite sleeve — see memory). → **Resolution:** never
auto-trim on weight/size. Port stop/target/reward:risk only as *informational* trade-plan
fields. Weight stays a neutral stat, never a warning or trigger.

**C2 — Decision vocabulary mismatch.** They emit `watch/candidate/enter/hold/trim/exit`
(entry-centric, for names you don't yet own). We emit `pile_on/hold/trim/exit` (for names
you hold). → **Resolution:** keep our action model as the user-facing decision. Their signals
become *inputs*, not a competing output. "candidate/enter" don't apply (we hold everything);
non-held names get a `watch-only` tag with signals shown but no sizing action.

**C3 — RSI semantics.** They treat RSI<30 as "eligible_to_buy" and >70 as
"eligible_to_trim_or_sell." We treat low RSI as a mild *add* signal and high RSI as
"don't chase" — but overbought is **not** a trim for us (overbought ≠ thesis break). →
**Resolution:** RSI (and "extended above MA") is a **timing modifier only**: it can demote a
would-be `pile_on` to `hold` ("don't chase"), and flag a name for review, but never by
itself produces `trim`. Threshold reconciliation: adopt their tested bands (oversold <30 /
overbought >70) — **this changes our current 35/70** (decision needed, §10).

**C4 — Duplicate / divergent indicator math.** Their `technicals.py` uses **Wilder RSI**,
EMA-based MACD, 252-bar 52w-high; our `market_data.py` has a *simpler rolling* RSI and its
own SMA/52w. Porting theirs without removing ours = two implementations → divergent numbers
on the same screen. → **Resolution:** adopt their `technicals.py` as the **single** technicals
source; delete our duplicate RSI/SMA/52w calcs and call the ported functions. ⚠️ **This is
part of "the evaluation system changing": RSI values will shift slightly** (Wilder vs simple).
Expected and correct; flagged here so it's not a surprise in review.

**C5 — Threshold gates vs LLM judgment.** Their fundamental layer is pass/fail thresholds
(rev growth ≥15% = pass). We lean on LLM judgment. → **Resolution:** fundamentals become
quantitative **inputs** (Signals) + thesis-break flags; they inform the provisional lean and
are handed to the LLM, but **no single threshold auto-fires an action.** The LLM weighs them.

**C6 — Refresh cadence.** Their engine assumes a nightly Russell-3000 cache; we fetch
on-demand twice daily for ~21 names. Fundamentals (quarterly) change rarely. → **Resolution:**
cache fundamentals in a table; refresh weekly + on earnings, not every run. Technicals/price
stay per-run.

**C7 — "Never training data for facts."** Aligns — no conflict. P/E and growth must be
sourced + timestamped (their `Signal.source_ref` + our memory rule reinforce each other).

**C8 — Label drift.** They call ATR-ish move "daily swing," 52w distance conventions match.
Minor → standardize labels in the glossary (single source of truth, §6) so nothing diverges.

---

## 4. The reworked decision engine — BEFORE → AFTER (laid out clearly)

### BEFORE (v1, current)
- Inputs: price, returns, simple technicals (RSI/SMA/ATR/52w/relvol/trend), RS vs SPY,
  position, earnings, analyst, news.
- `signals.build_signals` → badges + a `provisional_lean` from trend/RSI/extended/analyst
  (+ earnings guard; weight excluded).
- LLM routine → `final_lean` + `rationale` (subscription); trim only on thesis break.

### AFTER (v2) — three explicit layers
**Action set (v2):** `pile_on` · `hold` · `trim` · `exit` (+ `watch` for non-held names).
- `trim` = reduce but keep the position (respects the **$200 floor**) — for *partial* deterioration / reduced conviction.
- `exit` = close the position fully (**overrides the $200 floor** — you no longer want any) — for a *clear* thesis break.

**Layer 1 — Signal generation (Python, pure, with provenance).** For each metric emit a
`Signal{category, metric, value_num|value_text, passed|state, suggestion, source_type,
source_ref, insufficient_data}`:
- *Technical:* RSI(Wilder), MACD state, MA-cross state (golden/death/above/below),
  dist-to-support, dist-to-resistance, breakout(+vol), rel-vol, ATR%, dist-52w-high, trend.
- *Relative strength:* vs SPY (and optionally sector ETF — §10).
- *Fundamental:* revenue growth YoY, EPS growth YoY, gross-margin trend, P/E vs own ~8-qtr history.
- *Risk / trade-plan (informational only):* dist-to-stop, dist-to-target, reward:risk — **never auto-acts.**
- *Deterioration signals (can push toward trim/exit):* quant thesis-break flags (revenue QoQ
  drop ≥ X pp, gross-margin QoQ drop ≥ Y pp, ≥2 EPS misses in last 3 quarters), **confirmed
  downtrend** (death cross / price < 50d < 200d), **sustained negative relative strength**,
  weakening fundamentals (rev/EPS growth rolling over).
- *Event guard:* days to next earnings.

**Layer 2 — Provisional lean (transparent rules).** Explicit truth table, checked in order:

| Condition | Lean |
|---|---|
| Not held (shares = 0) | `watch` — signals shown, no sizing action |
| **Clear thesis break** — a quant thesis-break flag fires, OR (LLM layer) guidance cut / catalyst failed / quality gone | `exit` — close fully (overrides the $200 floor) |
| **Deterioration confluence** — ≥2 of {confirmed downtrend, weakening fundamentals, sustained negative RS, repeated EPS misses} but not a clean break | `trim` — reduce, keep ≥ $200 |
| **Strength** — uptrend / golden-cross / +RS, AND not overbought, AND not extended, AND not ≤1 trading day to earnings, AND fundamentals intact | `pile_on` |
| Otherwise | `hold` (incl. overbought / extended = "don't chase") |

**Invariants:**
- Deterioration drives `trim`/`exit` — **the thesis (growth/quality/theme/trend/fundamentals) going wrong is the reason.**
- **Position weight / % of the sleeve is NEVER a reason** for `trim` or `exit`. It's a small satellite sleeve; concentration within it is not a risk.
- Overbought / extended / a *single* mild negative reading → at most `hold` ("don't chase"), never `trim` on its own. Severity/confluence matters.

**Layer 3 — LLM final lean (routine, on subscription).** Receives the snapshot + all Signals
+ deterioration flags + news + earnings recap. Applies the **qualitative judgment the quant
can't see** (guidance cut, catalyst failure, management/regulatory) and weighs *severity* —
escalating `trim`→`exit` or de-escalating when the deterioration looks like noise. Writes
`final_lean` + `rationale`, may override the provisional lean, but **must cite the specific
driver**. Unchanged hard rules: trims/exits are driven by deterioration, **never by size**;
no sizing into a print; `trim` respects the $200 floor (`exit` doesn't); decision-support, not advice.

> Net change vs v1: the lean is now driven by an explicit, auditable signal set (incl.
> fundamentals + deterioration flags), adds an `exit` action for clear thesis breaks, lets a
> *confluence* of deterioration (not just a single formal flag) justify a `trim`, and keeps the
> hard ban on size-motivated trims. The LLM remains the final arbiter and severity-judge. The
> glossary (§6/§7) describes exactly this.

---

## 5. Data model / storage changes (additive, backward-compatible)
- **Migration `0002`**: new `fundamentals` table — `(ticker, fiscal_period, report_date,
  revenue, revenue_yoy, eps, eps_yoy, gross_margin, pe, source, fetched_at)`.
- Reuse existing `watchlist.target` / `watchlist.stop` for the trade-plan panel (optionally add `reward_multiple`).
- **Snapshot payload** gains (additive): `technicals.{macd, ma_cross, support, resistance, breakout}`,
  `fundamentals{...}`, `signals[]` (the Signal list with provenance), `thesis_break{flags}`,
  `trade_plan{stop, target, reward_risk}`. Old fields stay; the app degrades gracefully if absent.

---

## 6. Metrics registry — single source of truth (so the glossary can't drift)
- New `tracker/metrics.py` (or `config/metrics.yaml`): each metric defines `key, label,
  category, definition, how_computed, good_when, source_type`. The pipeline tags every Signal
  with its `key`; the web glossary renders from the **same** registry (served via an API
  route or a generated JSON). One fact, one home — the explanation is generated from the
  thing it explains.

---

## 7. Web app changes
- **New tab `/methodology` (Dictionary):**
  - **Metrics** — cards from the registry: plain definition, how it's computed, what "good"
    looks like, data source.
  - **How recommendations are made** — the §4 engine in plain English: the three layers, the
    truth table, trim-only-on-thesis-break, the satellite-sleeve no-concentration-trim rule,
    the $200 floor, "decision-support not advice."
  - **Data & freshness** — sources, refresh cadence, and the "never training-data facts" rule.
- **Drill-down upgrades:** MACD chip, support/resistance lines on the chart, a fundamentals
  mini-panel, and thesis-break flags when present — each metric label links to its glossary entry.
- **Nav:** add a Methodology link in the recap header.

---

## 8. Implementation order (phases, each TDD with a gate)

Implementation runs end-to-end in one pass, but **each phase is gated**: write that phase's
tests first (red), implement until green, run the gate, and only then proceed. If a gate
fails and can't be fixed cleanly, STOP and report rather than build on a broken layer. Test
catalogue in §8.5.

0. **P0 — test harness.** `requirements-dev.txt` (pytest, pytest-mock), `tests/` + `conftest.py`
   with fixtures (synthetic price/volume arrays with known outcomes; a fake snapshot; a fake
   fundamentals payload; a throwaway Postgres schema for storage tests). **Gate:** `pytest -q` runs green (0 tests OK).
1. **P1 — technicals port.** Port `technicals.py` **and** `test_technicals.py` from checklist-tab;
   integrate into `market_data`; delete duplicate RSI/SMA/52w. **Gate:** §8.5/T1 + a "single RSI impl" guard.
2. **P2 — Signal model + metrics registry.** **Gate:** §8.5/T2 (registry↔signals parity, no drift).
3. **P3 — fundamentals** (FMP + yfinance fallback) + `fundamentals` table + migration `0002`.
   **Gate:** §8.5/T3 (mocked source math + graceful degradation + migration round-trip).
4. **P4 — thesis-break flags.** **Gate:** §8.5/T4 (boundary + no false-positive on missing data).
5. **P5 — decision engine** (§4 truth table) + update `ROUTINE.md` LLM contract. **Gate:** §8.5/T5
   (full truth table + the invariant tests — this is the go/no-go).
6. **P6 — web** glossary tab (from registry), drill-down signals, chart S/R lines. **Gate:** §8.5/T6
   (build + typecheck + glossary↔registry parity + action-set consistency).
7. **P7 — wire-up + e2e.** **Gate:** §8.5/T7 (pipeline smoke on a test DB + v1 backward-compat),
   then regenerate enrichment and review on localhost.

## 8.5 Test design (write these first — they're the phase gates)

**Conventions:** unit/logic tests are **offline + deterministic** (no network) — those are the
gates. Real-API checks (FMP/Finnhub/yfinance) are marked `@pytest.mark.integration` and run
manually/nightly, never block a gate. Web checks reuse `tsc --noEmit` + `next build`.

**T1 — technicals (P1)**
- Port checklist-tab's `test_technicals.py` verbatim (RSI Wilder, MACD + crossover states,
  golden/death cross, swing pivots, dist-to-support/resistance, breakout+volume, 52w).
- Characterization: flat series → RSI 50; strictly rising → RSI→100; hand-built golden-cross
  series → `state == "golden_cross"`; insufficient history → `None` (not a crash).
- **C4 guard:** assert the pipeline uses exactly one RSI implementation (old `_rsi` removed;
  `market_data` calls `technicals.rsi`). Grep/AST or import-level assertion.

**T2 — Signal model + registry (P2)**
- Every emitted `Signal` has `category`, `metric`, `source_type`; `metric` ∈ registry keys.
- **No drift, both directions:** every registry key is emitted by some generator; every emitted
  metric has a registry entry. (This is the guard that the glossary can't lie.)
- Short-history input → `insufficient_data=True` (no fabricated value).

**T3 — fundamentals (P3)**
- Mocked FMP/yfinance payload → correct `revenue_yoy`, `eps_yoy`, gross-margin trend, P/E-vs-history.
- Source returns empty/None → fundamentals Signals flagged `insufficient_data`; pipeline doesn't crash.
- Migration `0002` applies on a throwaway schema; `fundamentals` row round-trips.

**T4 — thesis-break flags (P4)**
- Boundary tests: revenue QoQ drop at/above vs below threshold; margin drop; ≥2 EPS misses in
  last 3 vs 1 miss. Each toggles the flag correctly.
- Missing/insufficient fundamentals → flag is `None`/insufficient, **never a false `True`**.

**T5 — decision engine (P5) — the go/no-go gate**
- **Truth-table coverage** (one parametrized case per §4 row): not-held→`watch`; thesis-break
  flag→`exit`; ≥2 deterioration signals (no clean break)→`trim`; strength+room→`pile_on`;
  otherwise→`hold`.
- **"Don't chase":** strong + overbought → `hold` (NOT `pile_on`, NOT `trim`).
- **Severity guard:** a *single* mild negative (e.g. just-below-50d) → `hold`, not `trim`.
- **Event guard:** would-be `pile_on` within ≤1 trading day of earnings → `hold`.
- **C1 invariant (size never matters):** identical signals at weight 5% vs 90% → **identical lean**;
  a 90%-weight position with everything healthy is NOT `trim`/`exit`.
- **Determinism:** same inputs → same provisional lean.

**T6 — web (P6)**
- `tsc --noEmit` + `next build` pass.
- **Glossary↔registry parity:** the data the methodology page renders == the metrics registry
  (assert on the served JSON/registry, so docs can't drift from code).
- **Action-set consistency:** the documented actions == the code's action enum
  (`pile_on|hold|trim|exit|watch`) — one source, asserted equal.

**T7 — end-to-end (P7)**
- Pipeline smoke on a test DB: snapshot contains `technicals.macd`, `fundamentals`, `signals[]`,
  `thesis_break`, and a lean ∈ {pile_on,hold,trim,exit,watch} for every ticker; no exceptions.
- **Backward-compat:** the app renders a v1-shaped snapshot (new fields absent) without crashing.

---

## 9. Review plan
- After implementation, **two independent agent reviews of the branch diff**, with distinct mandates:
  1. **Correctness & contradictions** — bugs, divergent numbers, any place the port silently
     re-introduced size-based trims or duplicated math (C1–C8 checklist).
  2. **Decision-logic soundness & glossary fidelity** — does the engine match §4, and does the
     glossary text match the actual code/registry (no drift)?
- Reviewers also vet the **tests themselves** (§8.5): are the invariants actually asserted
  (esp. T5 C1 "size never matters" and the "don't chase" / severity guards), or vacuous? Were
  any gates weakened to pass? Green tests aren't enough — the assertions must be real.
- I fix findings, then hand you a **localhost** for your own review before merge.

---

## 10. Decisions — RESOLVED (2026-06-04)
1. **RSI bands:** ✅ adopt **30/70** (with Wilder RSI from the port).
2. **Fundamentals source:** ✅ **FMP** (your key) with yfinance fallback.
3. **Sector-relative strength:** ✅ later (keep SPY for now).
4. **Stop/target entry in the app:** ✅ add now (reuse the `target`/`stop` columns); reward:risk shown, **never auto-acts**.
5. **Glossary:** ✅ tab now; metric labels link to it; tooltips later.
6. **Trim/exit logic (user clarification):** trim *and* exit are valid when the thesis
   genuinely deteriorates (thesis break / downtrend / weakening fundamentals / negative RS) —
   confluence → trim, clear break → exit. **Position size / % of sleeve is never a reason.**
   Folded into §3 C1 and §4.
