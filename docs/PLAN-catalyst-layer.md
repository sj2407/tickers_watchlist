# PLAN — Catalyst / event layer

## Motivation

The engine is **structurally asymmetric**. Thesis *deterioration* is first-class:
`thesis_break.margin_compression` (+ `margin_severe`) is a measured, gated flag → a row on
the "Why this call" matrix → a `deterioration` dimension in `signals.provisional_lean` that
can move the quant lean. Forward-looking *catalysts* have **no structured representation at
all** — a PT upgrade, a partnership, an M&A close, a launch, an alt-data inflection, a
regulatory decision can only appear as a sentence the routine may or may not write into
`catalyst_summary`/`takeaway`, sourced from a thin Finnhub company-news feed
(`sources.company_news`, ~4-day lookback, 8 items) that in practice misses them.

Consequences we've observed:
- Analyst **PT revisions are invisible**: `price_targets.fetch_target` stores only
  aggregate low/median/mean/high. A Street-high raise dissolves into `high` with no firm,
  no date, no "raised today" event.
- Catalysts don't get a **history** the way the lean now does — `catalyst_summary` is
  overwritten each run, so there's no event log to review over time.
- The one catalyst that does surface can be **one-sided** (e.g. an FDA date framed only
  through the bear headline, missing the offsetting bull read).

## Goal / non-goals

**Goal:** capture forward-looking events as **structured, sourced, dated, two-sided**
records that (a) show on the board with their own history and (b) are available to the
routine as explicit inputs — symmetric to `thesis_break`.

**Non-goals (v1):**
- Do **not** let catalysts mechanically move the quant lean. Keep the existing philosophy:
  the quant proposes on deterioration and caps at trim; the LLM owns escalation. Catalysts
  enter the lean only through the routine's *qualitative* judgement, and must be justified
  via `lean_change_reason` (already built). Auto-influence is revisited only after backtest.
- No paid alt-data vendor in v1 (spend-tracker data is directional context, not a signal).

## Data model

New append-only table `events` (mirrors `transactions`/`snapshots` conventions):

```sql
CREATE TABLE events (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticker       text        NOT NULL,
  kind         text        NOT NULL,   -- see taxonomy below
  headline     text        NOT NULL,   -- one-line, plain English
  direction    text        NOT NULL CHECK (direction IN ('bull','bear','two_sided','neutral')),
  magnitude    text,                   -- 'minor' | 'notable' | 'major' (routine-graded)
  event_date   date,                   -- when it happens/happened (catalysts can be future)
  observed_at  timestamptz NOT NULL DEFAULT now(),
  source_name  text        NOT NULL,   -- e.g. 'Canaccord', 'company PR', 'FDA'
  source_url   text        NOT NULL,   -- REQUIRED — reputable, attributable
  detail       text,                   -- 2-3 sentence context incl. the counter-read
  dedup_key    text        NOT NULL,   -- ticker|kind|normalized-headline|event_date
  UNIQUE (dedup_key)
);
CREATE INDEX events_ticker_idx ON events (ticker, event_date DESC);
```

### Taxonomy (`kind`)
- `analyst_action` — rating/PT change. Structured extras in `detail`: firm, old→new PT,
  old→new rating. This is the highest-value, most-sourceable class.
- `corporate` — M&A close, product launch, guidance raise/cut, buyback, management change.
- `commercial` — partnership/customer/channel (e.g. the Novo relationship).
- `regulatory` — FDA/agency decisions, advisory-committee composition, legal.
- `alt_data` — directional, low-confidence (card spend, web traffic); always `magnitude<=notable`.

### Hard rules (carried from `ROUTINE.md`)
- **`source_url` is mandatory and must be reputable** — analyst desks, company PRs/filings,
  the agency itself, tier-1 press. No headline-aggregator scrapes as the sole source.
- **Two-sided by default** — if an event cuts both ways (the FDA lesson), `direction` is
  `two_sided` and `detail` must state *both* reads. A `bull`/`bear` label requires the
  counter-read to be genuinely weak.
- **Never training-data facts** — every event traces to `source_url`.

## Sourcing pipeline

1. **Analyst actions** — the biggest gap. Options, in order of preference: a provider with
   per-analyst actions + dates (evaluate FMP upgrades/downgrades, Benzinga, TipRanks API),
   falling back to routine web-search extraction when no feed. Diff `price_targets` snapshot
   to snapshot to *detect* an aggregate move, then web-search to *attribute* it.
2. **Corporate/commercial/regulatory** — routine web-search on full runs, constrained to
   reputable domains, extracting the structured record above (not prose).
3. **Dedup** — on `dedup_key`; the routine only inserts genuinely new events. Existing rows
   are never rewritten (append-only), so the event history is intact for review.

Python does the deterministic parts (PT diffing, dedup, persistence); the routine does the
sourcing + two-sided grading — same division of labor as today.

## Surfacing (web)

- **Catalysts section** on the ticker page: upcoming (future `event_date`) and recent,
  each a chip colored by `direction` with source link + the two-sided `detail`.
- **Markers on the price chart** at `event_date` for past events (reusing the marker
  primitive just added for trades).
- **Catalyst history** — symmetric to the new lean history: a query over `events`
  (or over `snapshots` payloads) so you can review what was known and when.
- The decision matrix stays deterioration-only in v1; a small "Catalysts in play" note sits
  beside it, explicitly *context, not a rule input*.

## Influence on the lean (the key decision)

**v1: context-only.** Catalysts are shown and handed to the routine, but the *quant* lean
ignores them. If the routine acts on a catalyst, it must say so in `lean_change_reason`
("FDA decision now 3 weeks out"), which the UI already surfaces as an override.

**v2 (post-backtest, gated):** consider a structured `catalyst_bias` that can *widen or
narrow* the pile/trim thresholds (never flip them outright), only for high-confidence,
sourced, non-alt-data events. Requires the same backtest bar as any `hard_dimensions`
change (see `PLAN-v2.md` §4 / D2).

## Phased rollout

1. **Schema + persistence** — `events` table, migration, `store`/`db` helpers, snapshot
   carry (latest N events per name), types.
2. **Analyst-action capture** — PT-diff detector + attribution; the highest-value slice.
3. **Web surfacing** — Catalysts section, chart markers, catalyst history.
4. **Routine integration** — `ROUTINE.md` step to source/grade events two-sided; wire into
   `catalyst_summary` from structured records instead of raw headlines.
5. **(Later, gated)** — evaluate v2 lean influence against a backtest.

## Open questions
- Which analyst-action provider clears the "reputable + dated + affordable" bar on the
  current data plan? (Same tier limitation that blocks per-analyst PT quartiles today.)
- Retention/dedup window for `alt_data` (noisy, revised often).
- Do future-dated catalysts need their own "T-minus" alerting, like the earnings cadence?
