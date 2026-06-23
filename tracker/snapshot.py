"""Build the snapshot JSON the routine + web app consume.

This orchestrates the dumb layer only. It leaves placeholder fields
(`catalyst_summary`, `earnings_recap`, `final_lean`, `rationale`) empty — the
Claude routine fills those in during its run, on the subscription.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from . import market_data as md
from . import sources, signals, store, thesis, api_cache, triggers, db, price_targets
from .calendar_utils import session_phase
from .config import load_config, load_env


def _price_series(hist: pd.DataFrame, sessions: int = 180) -> list[dict[str, Any]]:
    """Compact OHLC tail for charting: [{t, o, h, l, c, v}, ...] (date ascending)."""
    if hist.empty:
        return []
    tail = hist.tail(sessions)
    out = []
    for ts, row in tail.iterrows():
        # Skip bars with no close (e.g. a current-day partial bar in preopen): a NaN
        # close is unchartable and, left in, serializes to invalid JSON `NaN` that
        # Postgres rejects on insert.
        if not pd.notna(row["Close"]):
            continue
        out.append(
            {
                "t": ts.date().isoformat(),
                "o": round(float(row["Open"]), 2) if pd.notna(row["Open"]) else None,
                "h": round(float(row["High"]), 2) if pd.notna(row["High"]) else None,
                "l": round(float(row["Low"]), 2) if pd.notna(row["Low"]) else None,
                "c": round(float(row["Close"]), 2),
                "v": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
            }
        )
    return out


def _days_until(target: date | None, ref: date) -> int | None:
    if target is None:
        return None
    return (target - ref).days


def _next_earnings(ticker: str, today: date, bypass_cache: bool = False) -> dict[str, Any]:
    """Next upcoming + last reported earnings. UPCOMING dates trust Finnhub's
    CONFIRMED calendar first — yfinance's future dates are often estimates that can
    be days off, so they're used only when Finnhub has nothing (and flagged
    `next_date_estimated` when Finnhub outright FAILED rather than answered empty).
    Past dates keep the union (actuals come from Finnhub rows). Calendar cached per
    ET day; full runs bypass so post-close re-fetches a reporting day's actuals."""
    out: dict[str, Any] = {}
    cal = api_cache.cached(
        f"finnhub:earncal:{ticker}",
        lambda: sources.earnings_calendar(ticker),
        bypass=bypass_cache,
    )  # None = transport failure (uncached); [] = confirmed empty
    yf_dates = sources.earnings_dates_yf(ticker)

    cal_dates = []
    for row in (cal or []):
        try:
            cal_dates.append((date.fromisoformat(row["date"]), row))
        except (TypeError, ValueError):
            continue

    fh_upcoming = sorted(d for d, _ in cal_dates if d >= today)
    if fh_upcoming:
        upcoming = fh_upcoming
    else:
        upcoming = sorted(d for d in set(yf_dates) if d >= today)
        if cal is None and upcoming:
            out["next_date_estimated"] = True  # yf estimate, Finnhub didn't answer

    past = sorted(d for d in ({d for d, _ in cal_dates} | set(yf_dates)) if d < today)

    if upcoming:
        nxt = upcoming[0]
        out["next_date"] = nxt.isoformat()
        out["days_until_next"] = _days_until(nxt, today)
        for d, row in cal_dates:
            if d == nxt:
                out["next_hour"] = row.get("hour")
                out["next_eps_estimate"] = row.get("eps_estimate")
                out["next_revenue_estimate"] = row.get("revenue_estimate")
    if past:
        last = past[-1]
        out["last_date"] = last.isoformat()
        for d, row in cal_dates:
            if d == last:
                out["last_eps_estimate"] = row.get("eps_estimate")
                out["last_eps_actual"] = row.get("eps_actual")
                out["last_revenue_estimate"] = row.get("revenue_estimate")
                out["last_revenue_actual"] = row.get("revenue_actual")
    # surprise flags for the most recent reported quarter (numbers only; narrative is the routine's job)
    ea, ee = out.get("last_eps_actual"), out.get("last_eps_estimate")
    if ea is not None and ee not in (None, 0):
        out["last_eps_surprise_pct"] = round((ea - ee) / abs(ee) * 100, 1)
    return out


def build_ticker_row(tk, h, q, last, cfg, today, bench_hist, book_value, holdings, mode):
    """Build ONE ticker's full snapshot row (quant only; narrative left null). Shared by
    build_snapshot's loop and the append-one-ticker path so there's no duplicated logic."""
    closes = h["Close"].dropna() if not h.empty else None
    prev_close = q.get("prev_close")
    if prev_close is None and closes is not None and len(closes) >= 2:
        prev_close = round(float(closes.iloc[-2]), 2)
    if q.get("day_high") is None and not h.empty:
        q["day_high"] = round(float(h["High"].dropna().iloc[-1]), 2)
        q["day_low"] = round(float(h["Low"].dropna().iloc[-1]), 2)
    q["prev_close"] = prev_close

    tech = md.compute_technicals(h)
    rs = md.relative_strength(h, bench_hist)
    rets = md.compute_returns(h)
    series = _price_series(h, sessions=180)
    # Earnings first, so fundamentals can be freshness-gated against the latest report.
    earn = _next_earnings(tk, today, bypass_cache=(mode in ("preopen", "postclose")))
    fund = store.get_fundamentals(tk, earnings=earn)
    if not fund.get("pe"):
        ettm = fund.get("eps_ttm")
        fund["pe"] = round(last / ettm, 1) if (last and ettm and ettm > 0) else None
    extras = store.get_market_extras(tk)
    pos = md.position_math(holdings.get(tk), last, book_value or None)

    row: dict[str, Any] = {
        "ticker": tk,
        "price": {
            "last": last, "prev_close": q.get("prev_close"), "open": q.get("open"),
            "day_high": q.get("day_high"), "day_low": q.get("day_low"),
            "day_change_pct": md._pct(last, q.get("prev_close")),
        },
        "returns": rets, "relative_strength": rs, "technicals": tech, "fundamentals": fund,
        "thesis_break": thesis.thesis_break_flags(fund, cfg),
        "earnings_reaction": extras.get("earnings_reaction"), "scores": extras.get("scores"),
        "series": series, "position": pos, "earnings": earn,
        "analyst": api_cache.cached(f"finnhub:reco:{tk}", lambda tk=tk: sources.recommendation_trend(tk)),
        "price_target": api_cache.cached(f"yf:target:{tk}", lambda tk=tk: price_targets.fetch_target(tk)),
        "news": [],
        "takeaway": None, "sentiment": None, "catalyst_summary": None, "earnings_recap": None,
        "final_lean": None, "rationale": None,
    }
    row["signals"] = signals.build_signals(row, cfg)
    return row


def build_snapshot(mode: str) -> dict[str, Any]:
    load_env()
    sources.reset_finnhub_calls()  # per-run call + failure counters (data_health)
    cfg = load_config()
    tz = cfg["timezone"]
    today = datetime.now(ZoneInfo(tz)).date()
    tickers = store.get_tickers()       # DB watchlist, or config.yaml in file mode
    holdings = store.get_holdings()     # DB current_positions, or holdings.json

    # benchmarks (fetched once)
    bench_hist = sources.price_history(cfg["benchmark"], cfg["history_days"])

    rows: list[dict[str, Any]] = []
    intraday_triggered: list[str] = []
    # Fetch the prior enriched snapshot up front: used both to seed each row's prior
    # final_lean BEFORE computing intraday triggers (so a routine-marked trim/exit name
    # can't fire an entry trigger), and to carry the full narrative forward after the loop.
    prior = store.get_latest_enriched()
    prior_by_ticker = {t.get("ticker"): t for t in (prior or {}).get("tickers", [])}
    book_value = 0.0
    # first pass for book value (needs last prices)
    last_prices: dict[str, float | None] = {}
    hists: dict[str, pd.DataFrame] = {}
    quotes: dict[str, dict] = {}
    for tk in tickers:
        h = sources.price_history(tk, cfg["history_days"])
        hists[tk] = h
        q = sources.fast_quote(tk)
        quotes[tk] = q
        last = q.get("last_price")
        if last is None and not h.empty:
            last = round(float(h["Close"].dropna().iloc[-1]), 2)
        last_prices[tk] = last
        hold = holdings.get(tk)
        if hold and last:
            book_value += float(hold.get("shares") or 0) * last

    for tk in tickers:
        row = build_ticker_row(tk, hists[tk], quotes[tk], last_prices[tk], cfg, today,
                               bench_hist, book_value, holdings, mode)

        # Intraday = light entry-watch: only fetch news for names that trip a fresh
        # trigger (deduped once per ET day). Full runs always fetch news.
        if mode == "intraday":
            # Seed the routine's prior lean so triggers respect a trim/exit call (M2 fix).
            row["final_lean"] = (prior_by_ticker.get(tk) or {}).get("final_lean")
            trigs = triggers.compute_triggers(row, cfg)
            fresh = [tg for tg in trigs if (not db.using_db()) or db.claim_alert(tk, tg, today)]
            if fresh:
                intraday_triggered.append(tk)
                row["triggers"] = fresh
                row["news"] = sources.company_news(tk, cfg["news_lookback_days"], cfg["max_news_per_ticker"])
        else:
            row["news"] = sources.company_news(tk, cfg["news_lookback_days"], cfg["max_news_per_ticker"])

        rows.append(row)

    portfolio = _portfolio_block(rows, book_value)
    snap = {
        "generated_at": datetime.now(ZoneInfo(tz)).isoformat(),
        "mode": mode,  # preopen | intraday | postclose
        "session_phase": session_phase(tz),
        "as_of_date": today.isoformat(),
        "benchmark": cfg["benchmark"],
        "min_position_usd": cfg["min_position_usd"],
        "portfolio": portfolio,
        "tickers": rows,
        # filled by the Claude routine (carried forward below so it's NEVER null):
        "market_recap": None,
        "macro_context": None,
        "alerts": _mechanical_alerts(rows, cfg, mode),
        "intraday_triggered": intraday_triggered,
        "thresholds": {"big_move_pct": BIG_MOVE_PCT},
    }

    # Carry forward the prior run's narrative onto this fresh quant so no run — intraday
    # or full — ever publishes a null-narrative board. The routine then OVERWRITES it
    # (fully on full runs; for triggered names on intraday). Cold start: flag for the
    # routine to do a full narration instead of relying on a (nonexistent) prior.
    merge_narrative(snap, prior)  # prior fetched before the loop
    signals.validate_leans(snap)  # carried-forward leans must obey the vocabulary too
    grade_narrative_freshness(snap)
    snap["needs_full_enrichment"] = (prior is None)
    # Is the carried-forward market narrative older than the numbers it sits above?
    # (Reuses the per-ticker grader so the rule is identical and unit-tested.)
    snap["market_narrative_freshness"] = narrative_freshness(
        snap.get("market_narrative_as_of"), snap.get("generated_at"))
    # Deterministic overnight/global block — recomputed EVERY run (never carried),
    # so a 9am pre-open refresh always delivers fresh Asia/Europe/futures even when
    # the LLM narrative didn't regenerate.
    snap["global_markets"] = _global_markets_block(cfg)
    snap["data_health"] = _data_health(snap, mode)
    snap["performance"] = _performance_block(bench_hist, cfg, portfolio.get("unrealized_pl"))
    return snap


def _global_markets_block(cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Live overnight/global market moves (Asia + Europe + US futures), fetched
    fresh each run. None if the whole fetch fails — the UI then hides the strip
    rather than showing a stale one."""
    specs = cfg.get("global_markets") or sources.GLOBAL_MARKETS_DEFAULT
    markets: list[dict[str, Any]] = []
    for spec in specs:
        q = sources.recent_change(spec["symbol"])
        chg = md._pct(q.get("last"), q.get("prev_close")) if q else None
        if chg is None:
            continue
        markets.append({
            "symbol": spec["symbol"], "label": spec["label"], "region": spec["region"],
            "change_pct": chg, "last": q.get("last"), "as_of_date": q.get("as_of_date"),
        })
    if not markets:
        return None
    return {"as_of": datetime.now(ZoneInfo(cfg["timezone"])).isoformat(), "markets": markets}


def _performance_block(bench_hist: pd.DataFrame, cfg: dict[str, Any],
                       unrealized_pl: float | None = None) -> dict[str, Any] | None:
    """Sleeve TWR vs SPY/QQQ from the stored snapshot history (P10). None in file
    mode or on any failure — never blocks a run."""
    if not db.using_db():
        return None
    from . import performance

    try:
        history = [{"as_of_date": str(r["as_of_date"]), "book_value": r["book_value"],
                    "invested": r["invested"]} for r in db.fetch_book_history()]
        # Exact ledger flows (proceeds for sells, cost for buys) — never the
        # invested-delta approximation in production (review R1-1).
        flows = {r["d"]: {"buys": float(r["buys"]), "sells": float(r["sells"])}
                 for r in db.fetch_daily_flows()}
        spy = {ts.date(): float(v) for ts, v in md._return_closes(bench_hist).items()} \
            if not bench_hist.empty else None
        qqq_hist = sources.price_history("QQQ", cfg["history_days"])
        qqq = {ts.date(): float(v) for ts, v in md._return_closes(qqq_hist).items()} \
            if not qqq_hist.empty else None
        return performance.compute_performance(
            history, spy=spy, qqq=qqq, flows=flows,
            realized_pl=round(db.fetch_total_realized_pl(), 2),
            unrealized_pl=unrealized_pl,
        )
    except Exception:
        return None


def _data_health(snap: dict[str, Any], mode: str) -> dict[str, Any]:
    """Fetch-quality summary (P8): degraded data must never render like quiet data."""
    from . import cache_source

    rows = snap.get("tickers", [])
    cache_ts = cache_source.get_fmp_refreshed_at()
    age_h = None
    if cache_ts is not None:
        age_h = round((datetime.now(timezone.utc) - cache_ts).total_seconds() / 3600, 1)
    return {
        "finnhub_calls": sources.finnhub_call_count(),
        "finnhub_failures": sources.finnhub_failure_count(),
        # news is only fetched for every name on FULL runs; intraday fetches
        # triggered names only, so "missing" is meaningless there.
        "tickers_missing_news": ([r["ticker"] for r in rows if not r.get("news")]
                                 if mode in ("preopen", "postclose") else []),
        "tickers_missing_analyst": [r["ticker"] for r in rows if not r.get("analyst")],
        "equity_cache_used": cache_source.available(),
        "equity_cache_age_hours": age_h,
    }


# Narrative fields owned by the routine — carried forward verbatim when this run hasn't
# (re)generated them, so they're never dropped.
NARRATIVE_TICKER_FIELDS = (
    "takeaway", "sentiment", "catalyst_summary", "earnings_recap",
    "final_lean", "rationale", "entry_guidance", "invalidation",
    # validation provenance travels WITH the lean it explains (cleared when the
    # routine writes a fresh valid lean — see enrich.apply_enrichment):
    "lean_coerced_from", "lean_rejected",
    # when the routine last wrote this ticker's words — carried WITH them so a
    # stale narrative is always datable (P8):
    "narrative_as_of",
)

NARRATIVE_STALE_HOURS = 24
BIG_MOVE_PCT = 7.0  # single source for the alert AND the web movers chart (review R1-7)


def narrative_freshness(narrative_as_of: str | None, generated_at: str | None) -> str | None:
    """Tri-state narrative age vs the snapshot's numbers (P8) — computed in Python
    so it's unit-tested; the web renders it purely presentationally.
    fresh = written this run · carried = older but <24h · stale = >24h behind the
    numbers · None = never stamped (legacy snapshots)."""
    if not narrative_as_of or not generated_at:
        return None
    try:
        na = datetime.fromisoformat(str(narrative_as_of))
        ga = datetime.fromisoformat(str(generated_at))
    except ValueError:
        return None
    if na >= ga:
        return "fresh"
    if (ga - na).total_seconds() > NARRATIVE_STALE_HOURS * 3600:
        return "stale"
    return "carried"


def grade_narrative_freshness(snap: dict[str, Any]) -> None:
    """Stamp narrative_freshness on every row (in place)."""
    gen = snap.get("generated_at")
    for t in snap.get("tickers", []):
        t["narrative_freshness"] = narrative_freshness(t.get("narrative_as_of"), gen)
NARRATIVE_TOP_FIELDS = ("market_recap", "macro_context", "market_narrative_as_of")


def merge_narrative(fresh: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    """Copy prior narrative onto `fresh` wherever fresh hasn't set it (pure; in place).
    Covers ALL tickers (incl. would-be-triggered — the routine overwrites those) plus the
    top-level market recap/macro. None prior (cold start) → fresh is returned unchanged."""
    if not prior:
        return fresh
    prior_by_ticker = {t.get("ticker"): t for t in prior.get("tickers", [])}
    for t in fresh.get("tickers", []):
        p = prior_by_ticker.get(t.get("ticker"))
        if not p:
            continue
        for f in NARRATIVE_TICKER_FIELDS:
            if t.get(f) is None and p.get(f) is not None:
                t[f] = p[f]
    for f in NARRATIVE_TOP_FIELDS:
        if fresh.get(f) is None and prior.get(f) is not None:
            fresh[f] = prior[f]
    return fresh


def _portfolio_block(rows: list[dict[str, Any]], book_value: float) -> dict[str, Any]:
    held = [r for r in rows if r["position"].get("held")]
    total_pl = sum((r["position"].get("unrealized_pl") or 0) for r in held)
    invested = sum((r["position"].get("invested") or 0) for r in held)
    movers = [
        (r["ticker"], r["price"].get("day_change_pct"))
        for r in rows
        if r["price"].get("day_change_pct") is not None
    ]
    movers.sort(key=lambda x: x[1])
    return {
        "book_value": round(book_value, 2),
        "invested": round(invested, 2),
        "unrealized_pl": round(total_pl, 2),
        "unrealized_pl_pct": round(total_pl / invested * 100, 2) if invested else None,
        "positions_count": len(held),
        "top_gainer": movers[-1] if movers else None,
        "top_loser": movers[0] if movers else None,
    }


def _mechanical_alerts(rows: list[dict[str, Any]], cfg: dict[str, Any],
                       mode: str = "postclose") -> list[dict[str, Any]]:
    """Time-sensitive flags. IN-WINDOW, not exact-day (a skipped run used to mean a
    missed alert): the board is recomputed state, so the pill stays present on every
    run while relevant. big_move is suppressed at preopen — there, day_change is
    YESTERDAY's move, already alerted post-close. Narrative alerts come from the routine."""
    alerts = []
    for r in rows:
        tk = r["ticker"]
        days = r["earnings"].get("days_until_next")
        if days is not None and 1 < days <= 7:
            est = " (date unconfirmed)" if r["earnings"].get("next_date_estimated") else ""
            alerts.append({"ticker": tk, "type": "earnings_t7",
                           "msg": f"{tk} reports in {days}d ({r['earnings'].get('next_date')}){est}"})
        if days is not None and 0 <= days <= 1:
            when = "today" if days == 0 else "tomorrow"
            alerts.append({"ticker": tk, "type": "earnings_t1",
                           "msg": f"{tk} reports {when} ({r['earnings'].get('next_hour') or 'time TBD'})"})
        chg = r["price"].get("day_change_pct")
        if mode != "preopen" and chg is not None and abs(chg) >= BIG_MOVE_PCT:
            alerts.append({"ticker": tk, "type": "big_move", "msg": f"{tk} moved {chg:+.1f}% today"})
        # NOTE: no position-weight alert — this is a small satellite sleeve; size isn't a risk here.
    return alerts
