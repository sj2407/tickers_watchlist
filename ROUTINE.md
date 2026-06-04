# Routine spec — what the scheduled watchlist run does

This is the instruction set for the **single** scheduled routine (`~/.claude/scheduled-tasks/
watchlist/`), a Claude Code agent run on your **subscription** (not the API). It fires a few
times a day and **adapts to the market session** — the Python pipeline is the dumb plumbing
(it has produced `out/snapshot.json`); the routine adds the **qualitative layer** + delivery,
the work that would otherwise cost API tokens.

## When it runs (one routine, clock-branched)
Cron `5 9,13,16 * * 1-5` (≈ 9:05 / 1:05 / 4:05 ET, weekdays; jitter ~9 min). The mode is
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
   - **INTRADAY** (light): if `intraday_triggered` is empty, STOP (carried narrative stands). Else,
     for JUST those tickers, web-search what's moving them and write a SHORT entry note (`takeaway`
     + `entry_guidance`) into `out/enrichment.json` for those tickers only. Don't re-narrate the rest.
4. **Final one-line message:** preopen = pre-open watch list; intraday = the entry alerts only;
   postclose = recap (movers, beats/misses, lean changes). (Delivery = the task-completion
   notification; push/email is a future add.)

## Decision rules (the lean) — see docs/PLAN-v2.md §4
- Actions: `pile_on` · `hold` · `trim` · `exit` (`watch` for non-held). The **quant proposes
  pile_on/hold/trim**; **YOU (the LLM) own `exit`** — escalate `trim`→`exit` only on a *confirmed*
  break, weighing news/guidance/severity.
- **Trim/exit are driven by thesis DETERIORATION** (growth/quality/theme/trend/fundamentals going
  wrong) — **NEVER by position size / % of the sleeve** (small satellite sleeve).
- A single mild negative → `hold`; overbought → "don't chase" `hold`, never trim. No sizing into a
  print (≤1 day to earnings). `trim` keeps the $200 floor; `exit` closes fully.

## Hard rules
- **Subscription only** — do reasoning in the run; never call the Anthropic API / add an API key.
- **Never training-data facts** — prices/figures from the snapshot; news/earnings/macro via web search.
- **Never delete/null an output** — narrative is carried forward for all names; you only OVERWRITE
  (full: all; intraday: triggered). A failed enrich leaves the prior read intact.
- Decision-support, not advice — the user places every order.

## Earnings cadence (alerts)
- T-7: "reports in ~1 week" + last surprise. T-1: confirmed date/time + Street est + your P/L going in.
- Recap: EPS/rev beat-miss, guidance raise/cut/inline, reaction vs. the implied move, 2-3 call highlights.
