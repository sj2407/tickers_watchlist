# Routine spec — what the twice-daily Claude run does

This is the instruction set for the scheduled **routine** (a Claude Code agent run
on your **subscription**, not the API). The Python pipeline has already produced
`out/snapshot.json` with all the quantitative facts. The routine's job is the
**qualitative layer** + delivery — the work that would otherwise cost API tokens.

## When it runs
- **Pre-open** — ~09:00 ET, weekdays. Forward-looking: *what to watch today.*
- **Post-close** — ~16:30 ET, weekdays. Backward-looking: *what happened, does it change a position.*

## Steps each run
1. Run the pipeline: `python -m tracker.run --mode {preopen|postclose} --pretty`
2. Read `out/snapshot.json`.
3. Write your qualitative read to **`out/enrichment.json`** (don't hand-edit the snapshot),
   then merge it with `python -m tracker.enrich`. The overlay carries, per ticker:
   - `takeaway` — ONE plain-English line: what's going on + what to consider. This is the
     hero line on every card; make it readable to a non-quant.
   - `sentiment` — `bullish | bearish | neutral | mixed`.
   - `catalyst_summary` — 1–3 sentences from the `news` headlines: what's the catalyst
     (earnings / product / M&A / guidance / analyst action / macro), and which way it cuts.
     The Finnhub feed is noisy — **filter out headlines not actually about this name**.
   - `earnings_recap` — **only if it just reported** (look at `earnings.last_date` within
     ~2 sessions): EPS actual vs est, revenue actual vs est, **guidance raise/cut/inline**,
     and market reaction (`price.day_change_pct` / after-hours). Use web lookup for the call.
   - `final_lean` — `pile_on` | `hold` | `trim` | `exit` (`watch` for non-held). Start from
     `signals.provisional_lean` (the quant truth table), then apply the **qualitative
     judgment the quant can't see** (guidance cut, catalyst failure, management/regulatory)
     and weigh *severity*: escalate `trim`→`exit` on a clear break, or de-escalate when the
     deterioration looks like noise. You may override the provisional lean, but cite the driver.
     - **Trim/exit are driven by DETERIORATION** — thesis break, confirmed downtrend, weakening
       fundamentals, sustained negative relative strength. Confluence → `trim`; a clear break → `exit`.
     - **NEVER trim/exit on position size / % of the sleeve** — small satellite sleeve; size isn't
       a risk. A name being a large % of the book is fine if the thesis holds.
     - **Never size into a print** (≤1 day to earnings → don't escalate to a sizing change).
     - `trim` keeps ≥ the $200 floor; `exit` closes fully (only on a clear break).
   - `rationale` — one line citing the *specific* drivers (deterioration signals / catalyst),
     never position size.
   - `entry_guidance` — for adds: *where/when* ("good add zone — pulled back near support ~$X /
     RSI cooled" vs "extended at RSI 78 — wait, don't chase"). Use the support/resistance + RSI signals.
   - `invalidation` — the trigger stated *in advance*: what flips this call ("cut if rev growth
     <X%, guidance is cut, or it loses $Y support"; or "add becomes attractive on a pullback to $Z").
   - If a stop is set and breached (`technicals`/`position`), surface a **review prompt**
     ("price hit your stop — is the thesis still intact?") — never an auto-cut.
4. Write `market_recap` (1–2 sentences on the tape + the day's relevant macro) and
   `macro_context` (only macro that actually touches these names — rates, oil, the Fed, etc.).
5. Enrich `alerts` with narrative (earnings T-7 / T-1 and big moves are seeded mechanically
   — add anything material from the news). Do NOT add position-size / weight alerts.
6. **Deliver:** push the enriched snapshot to the app's DB, send the HTML email digest,
   and fire push alerts for time-sensitive items (earnings T-1, big gaps, halts).

## Earnings cadence (alerts)
- **T-7 days:** "reports in ~1 week" + last-quarter surprise + (later) implied move.
- **T-1 day:** confirmed date/time, Street EPS & revenue estimate, your unrealized P/L going in.
- **Recap:** EPS/rev beat-miss, guidance, market reaction vs. expectations, 2–3 call highlights.

## Hard rules
- **Subscription only.** Do all reasoning in the run. Never call the Anthropic API / add an
  `anthropic` client to the Python. Never print or commit secret values.
- **Decision-support, not advice.** Surface signals + a lean with reasons; the user places
  every order. $200 is the floor on any trim.
