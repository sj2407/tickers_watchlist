"""Deterministic synthetic market data shared by the P0 guard tests.

Everything is a pure function of (seed, base) over the REAL XNYS session calendar
ending at FIXED_END, so values are bit-stable across runs and machines — the
characterization and golden-snapshot tests hard-code numbers derived from these.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from tracker.calendar_utils import trading_sessions

FIXED_END = date(2026, 6, 9)  # a Tuesday, regular XNYS session
N_SESSIONS = 260              # > 200 so SMA200 / 52w stats are available


def sessions() -> list[date]:
    return trading_sessions(FIXED_END, lookback=300)[-N_SESSIONS:]


def price_frame(seed: int, base: float) -> pd.DataFrame:
    """OHLCV frame over the real session calendar; smooth uptrend + gentle sine."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in sessions()])
    i = np.arange(len(idx), dtype=float)
    close = base + i * 0.3 + 5 * np.sin(i / 7.0) + (seed * 3.0)
    vol = (1_000_000 + (i * 1000) + (seed * 500)).astype(int)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.2,
            "Close": close,
            "Volume": vol,
        },
        index=idx,
    )
