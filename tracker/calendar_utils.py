"""Trading-calendar helpers so 1d/5d/20d windows respect market holidays."""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal


@lru_cache(maxsize=4)
def _calendar(name: str = "XNYS"):
    return mcal.get_calendar(name)


def trading_sessions(end: date, lookback: int = 60, name: str = "XNYS") -> list[date]:
    """Return the trading session dates up to and including `end` (most recent last)."""
    cal = _calendar(name)
    start = end - pd.Timedelta(days=lookback * 2 + 10)
    sched = cal.schedule(start_date=start, end_date=end)
    return [d.date() for d in sched.index]


def is_trading_day(d: date, name: str = "XNYS") -> bool:
    cal = _calendar(name)
    sched = cal.schedule(start_date=d, end_date=d)
    return len(sched) > 0


def session_phase(tz: str = "America/New_York", name: str = "XNYS") -> str:
    """Rough phase of the current moment: premarket / open / afterhours / closed."""
    now = datetime.now(ZoneInfo(tz))
    today = now.date()
    if not is_trading_day(today, name):
        return "closed"
    cal = _calendar(name)
    sched = cal.schedule(start_date=today, end_date=today)
    if sched.empty:
        return "closed"
    open_t = sched.iloc[0]["market_open"].tz_convert(tz)
    close_t = sched.iloc[0]["market_close"].tz_convert(tz)
    if now < open_t:
        return "premarket"
    if now <= close_t:
        return "open"
    return "afterhours"


def resolve_mode(tz: str = "America/New_York", name: str = "XNYS") -> str | None:
    """Map the real market session to a run mode. None = market closed → no-op.
    premarket→preopen · open→intraday · afterhours→postclose · closed→None.
    Uses the actual XNYS schedule, so half-days and holidays route correctly."""
    phase = session_phase(tz, name)
    return {"premarket": "preopen", "open": "intraday", "afterhours": "postclose"}.get(phase)


def returns_window_dates(end: date, windows=(1, 5, 20), name: str = "XNYS") -> dict[int, date]:
    """Map each window N to the session date N trading days before `end`."""
    sessions = trading_sessions(end, lookback=max(windows) + 10, name=name)
    if end in sessions:
        idx = sessions.index(end)
    else:
        idx = len(sessions) - 1  # end not a session; use latest available
    out: dict[int, date] = {}
    for n in windows:
        j = idx - n
        if 0 <= j < len(sessions):
            out[n] = sessions[j]
    return out
