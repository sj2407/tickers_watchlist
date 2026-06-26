"""Config + secret loading.

Secrets are read from the existing equity-research-agent `.env` *in place* — we
never copy or duplicate key values. Point `WATCHLIST_ENV_FILE` at a different
path to override, or set a key directly in the real environment.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = Path.home() / "equity-research-agent" / ".env"
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


def load_env() -> None:
    """Load the shared .env (without copying it). Local real-env vars win."""
    env_file = Path(os.environ.get("WATCHLIST_ENV_FILE", DEFAULT_ENV_FILE))
    if env_file.exists():
        # override=False → anything already exported in the shell takes precedence
        load_dotenv(env_file, override=False)
    # Also pick up a project-local .env if the user makes one (gitignored).
    local = PROJECT_ROOT / ".env"
    if local.exists():
        load_dotenv(local, override=False)


def get_key(name: str) -> str | None:
    return os.environ.get(name)


def require_key(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing API key {name}. Expected it in {DEFAULT_ENV_FILE} "
            f"or the environment (set WATCHLIST_ENV_FILE to override)."
        )
    return val


_DEFAULTS: dict[str, Any] = {
    "timezone": "America/New_York",
    "benchmark": "SPY",
    "min_position_usd": 200.0,
    "history_days": 400,  # enough for 200-day MA + buffer
    "news_lookback_days": 4,
    "max_news_per_ticker": 8,
    "signals": {
        "rsi_overbought": 70,
        "rsi_oversold": 30,  # PLAN-v2 decision #1 (30/70 Wilder bands)
        "rel_vol_spike": 2.0,
        "extended_above_sma20_pct": 12.0,  # far above 20d MA → trim watch
        "earnings_soon_days": 7,
        # P4b (provisional, tunable — revisit with backtest evidence): dimensions
        # that count as HARD deterioration. A trim needs ≥2 dimensions incl. ≥1
        # hard; soft-only confluence → hold + Review badge. "margin_severe" means
        # margin_compression is hard only when the collapse is severe (≤ −5pp).
        "hard_dimensions": ["downtrend", "revenue_weakening", "margin_severe"],
    },
    "intraday": {
        "near_support_pct": 2.0,    # within 2% above nearest support → entry zone
        "rsi_buy_band": 45.0,       # RSI cooled to ≤ this → entry timing
        "sma50_zone_low": -4.0,     # pulled back into the 50-day zone (not a falling knife)
        "sma50_zone_high": 1.0,
        "notable_dip_pct": -5.0,    # held name down ≥5% on the day (thesis intact) → flag
    },
    "tickers": [],
    "sector_etf": {},  # optional ticker -> sector ETF for relative strength
    "theme": {},       # optional ticker -> theme bucket (grounds portfolio.composition)
}


def load_config() -> dict[str, Any]:
    cfg = dict(_DEFAULTS)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            user = yaml.safe_load(f) or {}
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                merged = dict(cfg[k])
                merged.update(v)
                cfg[k] = merged
            else:
                cfg[k] = v
    return cfg
