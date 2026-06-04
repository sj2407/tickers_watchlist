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
| E | **Reworked decision engine** combining all of the above into pile/trim/hold — explicitly (§4) | new |
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
(entry-centric, for names you don't yet own). We emit `pile_on/trim/hold` (for names you
hold). → **Resolution:** keep our 3-action model as the user-facing decision. Their signals
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
**Layer 1 — Signal generation (Python, pure, with provenance).** For each metric emit a
`Signal{category, metric, value_num|value_text, passed|state, suggestion, source_type,
source_ref, insufficient_data}`:
- *Technical:* RSI(Wilder), MACD state, MA-cross state (golden/death/above/below),
  dist-to-support, dist-to-resistance, breakout(+vol), rel-vol, ATR%, dist-52w-high, trend.
- *Relative strength:* vs SPY (and optionally sector ETF — §10).
- *Fundamental:* revenue growth YoY, EPS growth YoY, gross-margin trend, P/E vs own ~8-qtr history.
- *Risk / trade-plan (informational only):* dist-to-stop, dist-to-target, reward:risk — **never auto-acts.**
- *Thesis-break flags (quant):* revenue QoQ drop ≥ X pp, gross-margin QoQ drop ≥ Y pp,
  ≥2 EPS misses in last 3 quarters. **These are the only quant signals that can push toward `trim`.**
- *Event guard:* days to next earnings.

**Layer 2 — Provisional lean (transparent rules).** Explicit truth table:

| Condition (checked in order) | Provisional lean |
|---|---|
| Not held (shares = 0) | `watch` (signals shown, no sizing action) |
| Any **thesis-break flag** true | `trim` (the ONLY rule-based path to trim) |
| Strength (uptrend / golden-cross / +RS) AND **not** overbought AND **not** extended AND **not** ≤1 trading day to earnings AND fundamentals not deteriorating | `pile_on` |
| Otherwise | `hold` |

Key invariant: overbought / extended / downtrend / negative-RS at most produce `hold`
("don't chase" / "watch for deterioration") — **never `trim` on their own.** Size/weight
never appears here.

**Layer 3 — LLM final lean (routine, on subscription).** Receives the snapshot + all Signals
+ thesis-break flags + news + earnings recap. Applies the **qualitative thesis-break the quant
can't see** (guidance cut, catalyst failure, management/regulatory). Writes `final_lean` +
`rationale`. May override the provisional lean but **must cite the specific driver.**
Unchanged hard rules: trim only on thesis break; never on size; no sizing into a print;
$200 floor; decision-support, not advice.

> Net change vs v1: the lean is now driven by an explicit, auditable signal set (incl.
> fundamentals + thesis-break flags), the quant can only *trim* via a thesis-break flag, and
> the LLM remains the final arbiter for qualitative thesis breaks. The glossary (§6/§7) will
> describe exactly this.

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

## 8. Implementation order (phases; tests per phase)
1. **P1 — technicals port:** bring `technicals.py` + its tests; integrate into `market_data`;
   remove duplicate RSI/SMA/52w; verify numbers shift as expected (C4).
2. **P2 — Signal model + metrics registry:** provenance + `insufficient_data`; registry module.
3. **P3 — fundamentals:** source + `fundamentals` table + migration + cached fetch in the pipeline.
4. **P4 — thesis-break flags.**
5. **P5 — rework provisional-lean rules** (§4 truth table); update `ROUTINE.md` LLM final-lean contract.
6. **P6 — web:** glossary tab (from registry), drill-down signal surfacing, chart S/R lines.
7. **P7 — wire-up + verify** end-to-end on localhost; regenerate enrichment; sanity-check leans.

---

## 9. Review plan
- After implementation, **two independent agent reviews of the branch diff**, with distinct mandates:
  1. **Correctness & contradictions** — bugs, divergent numbers, any place the port silently
     re-introduced size-based trims or duplicated math (C1–C8 checklist).
  2. **Decision-logic soundness & glossary fidelity** — does the engine match §4, and does the
     glossary text match the actual code/registry (no drift)?
- I fix findings, then hand you a **localhost** for your own review before merge.

---

## 10. Open decisions for you (I'll proceed with the *proposed* default unless you say otherwise)
1. **RSI bands:** keep our 35/70, or adopt checklist's **30/70**? → *Proposed: 30/70* (tested, and Wilder RSI comes with the port).
2. **Fundamentals source:** yfinance quarterly (free, sometimes patchy) vs **FMP** (you have the key, cleaner). → *Proposed: FMP with yfinance fallback.*
3. **Sector-relative strength** (vs a sector ETF, not just SPY): add now or later? → *Proposed: later (keep SPY for now).*
4. **Stop/target entry in the app** to power the risk panel: now or defer? → *Proposed: add simple stop/target inputs now (they're already columns); reward:risk shown, never auto-acts.*
5. **Glossary:** tab only, or tab + inline tooltips on each metric? → *Proposed: tab now, metric labels link to it; tooltips later.*
