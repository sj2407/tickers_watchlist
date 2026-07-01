# Routine spec — what the scheduled watchlist run does

This is the instruction set for the **single** scheduled routine (`~/.claude/scheduled-tasks/
watchlist/`), a Claude Code agent run on your **subscription** (not the API). It fires a few
times a day and **adapts to the market session** — the Python pipeline is the dumb plumbing
(it has produced `out/snapshot.json`); the routine adds the **qualitative layer** + delivery,
the work that would otherwise cost API tokens.

## When it runs (one routine, clock-branched)
Cron `30 8,13,16 * * 1-5` (≈ 8:30 / 1:30 / 4:30 ET, weekdays; +several-min dispatch delay). The
morning fires pre-open with enough runway to finish enrichment (~15 min) and still leave time to
read and position before the 9:30 open. The mode is
resolved from the REAL market session via `tracker.run --mode auto` → `calendar_utils.resolve_mode`:
- **premarket → `preopen`** (full): forward-looking brief.
- **open → `intraday`** (light): entry-watch only.
- **afterhours → `postclose`** (full): recap incl. earnings.
- **closed (weekend/holiday/half-day-closed) → no-op:** logs and exits, **touching nothing** (prior snapshot stands).

## Steps each run
1. `python -m tracker.run --mode auto`. If it prints "market closed — no-op", STOP. Otherwise it
   prints the resolved mode and writes a snapshot to Neon that **already carries the prior
   narrative forward** (so the board is never blank), records the row id (for enrich-by-id), and
   sets `intraday_triggered` (list) + `needs_full_enrichment` (cold start).
2. Read `out/snapshot.json` — note `mode`, `intraday_triggered`, `needs_full_enrichment`.
3. **Enrich, by mode**, writing `out/enrichment.json` then `python -m tracker.enrich` (which
   publishes to the row this run inserted — no cross-run clobber):
   - **FULL** (preopen / postclose / `needs_full_enrichment`): regenerate the WHOLE layer for all
     tickers — `market` recap + macro, and per ticker `takeaway` (the hero line), `sentiment`,
     `catalyst_summary` (filter Finnhub noise), `earnings_recap` (if it just reported: EPS/rev
     beat-miss, guidance, reaction), `final_lean`, `rationale`, `entry_guidance`, `invalidation`.
     On a **preopen** brief, LEAD the recap with the overnight picture: the snapshot's
     `global_markets` block (Asia + Europe already trading, plus US index futures — fetched fresh
     every run, so it's never stale even if you don't regenerate) and overnight news/macro, with the
     read-through to held names (e.g. a Korea / memory-chip selloff into TSM, MU).
   - **INTRADAY** (light): if `intraday_triggered` is empty, STOP (carried narrative stands). Else,
     for JUST those tickers, web-search what's moving them and write a SHORT entry note (`takeaway`
     + `entry_guidance`) into `out/enrichment.json` for those tickers only. Don't re-narrate the rest.
4. **Final one-line message:** preopen = pre-open watch list; intraday = the entry alerts only;
   postclose = recap (movers, beats/misses, lean changes). (Delivery = the task-completion
   notification; push/email is a future add.)

## Decision rules (the lean) — see docs/PLAN-v2.md §4
- Actions: `pile_on` · `hold` · `trim` · `exit`. **Every tracked name is held** (the user keeps
  ~$200 in anything worth watching) — `watch` is NOT a valid lean for a held name and the
  pipeline will coerce it to `hold` with a visible `lean_coerced_from` flag. Never demote a
  quant `trim` proposal to a non-action label: if you disagree with the trim, write `hold`
  and address the deterioration drivers explicitly in the rationale. The **quant proposes
  pile_on/hold/trim**; **YOU (the LLM) own `exit`** — escalate `trim`→`exit` only on a *confirmed*
  break, weighing news/guidance/severity.
- **Trim/exit are driven by thesis DETERIORATION** (growth/quality/theme/trend/fundamentals going
  wrong) — **NEVER by position size / % of the sleeve** (small satellite sleeve).
- A single mild negative → `hold`; overbought → "don't chase" `hold`, never trim. No sizing into a
  print (≤1 day to earnings). `trim` keeps the $200 floor; `exit` closes fully.

### Justify every change — no stale datapoint as a fresh trigger
Each row carries two anchors you MUST read before writing `final_lean`:
- `signals.provisional_lean` — the quant's mechanical proposal this run.
- `prior_lean` — the call the board showed at your **last** run (Python-owned; you can't see a
  narrative diff otherwise).

When your `final_lean` differs from **either** anchor, you MUST also write `lean_change_reason`: one
sentence naming the **fresh, material development** that justifies acting *now* — a new print, new
guidance, a downgrade, a dated catalyst coming into range, a decisive price/technical break, a thesis
event since your last run. It answers "why now, and not last run?"
- **A standing fact is NOT a reason.** If margins have been compressing for two quarters, "margins are
  compressing" cannot justify a *new* trim today — that was already true at `prior_lean`. Either point
  to what changed (e.g. "guide cut on last night's print," "FDA decision now 3 weeks out"), or keep
  `prior_lean` and leave the lean unchanged.
- If you're **overriding the quant** (e.g. quant says `hold`, you write `trim`), `lean_change_reason`
  must carry the override's justification — the UI shows the quant proposed otherwise.
- If nothing material changed since `prior_lean`, keep the prior lean and set `lean_change_reason` to
  `null`. Do not re-narrate an unchanged call as if it were new.

## Hard rules
- **Subscription only** — do reasoning in the run; never call the Anthropic API / add an API key.
- **Never training-data facts** — prices/figures from the snapshot; news/earnings/macro via web search.
- **Never delete/null an output** — narrative is carried forward for all names; you only OVERWRITE
  (full: all; intraday: triggered). A failed enrich leaves the prior read intact.
- Decision-support, not advice — the user places every order.
- **Ground every claim about the book as a whole in `portfolio.composition`, never recall.**
  Any portfolio-LEVEL statement — counts ("two healthcare names", "X of N"), superlatives
  ("the only", "the one", "the biggest position", "most of the book"), or "off the AI complex"
  type groupings — must match the snapshot: `portfolio.composition.by_theme` (member list +
  count per theme) and the per-ticker `theme` field. "The AI complex" is the union of the
  semis/AI themes (memory, semicap equipment, foundry, AI silicon, optical/connectivity, AI
  infrastructure, software, semiconductor IP); names in other themes are NOT in it. If a name
  is under `composition.untagged`, you don't have ground truth for its bucket — don't assert one.
- **Don't narrate `data_health.equity_cache_age_hours` as staleness** — when that cache is >36h old
  the pipeline self-fetches fresh fundamentals, so its age is a diagnostic, not a data note. Only
  surface what the snapshot actually flags (`tickers_price_carried`, `tickers_missing_news`,
  per-ticker `fundamentals_stale`/`ttm_stale`).

## Narrative writing style (takeaway / catalyst / recap / rationale)
- **Never use em-dashes (—).** Use commas, semicolons, or periods. (En-dash ranges like `19-28%` are fine.)
- **Never describe direction with color words** ("GREEN", "RED", "in the green"). The app color-codes
  numbers and adds up/down arrows, so the word is redundant. Say "up 6%" / "down 6%" or just the signed
  number; the UI handles the color.
- Lead with the plain read; keep numbers in the prose (the app highlights them automatically).

## Earnings cadence (alerts)
- T-7: "reports in ~1 week" + last surprise. T-1: confirmed date/time + Street est + your P/L going in.
- Recap: EPS/rev beat-miss, guidance raise/cut/inline, reaction vs. the implied move, 2-3 call highlights.
