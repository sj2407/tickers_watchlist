"""Phase 0-2 gates: ET-day cache freshness + mode resolution (pure logic, offline)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from tracker import api_cache, calendar_utils

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def test_current_et_date_uses_eastern_not_host():
    # 01:30 UTC on Jun 5 is still Jun 4 in ET (21:30 prior day) — host-TZ-proof
    now = datetime(2026, 6, 5, 1, 30, tzinfo=UTC)
    assert api_cache.current_et_date(now) == date(2026, 6, 4)


def test_is_fresh_same_et_day_only():
    now = datetime(2026, 6, 4, 13, 0, tzinfo=ET)
    assert api_cache.is_fresh(date(2026, 6, 4), now) is True       # same ET day → fresh
    assert api_cache.is_fresh(date(2026, 6, 3), now) is False      # prior day → stale
    assert api_cache.is_fresh(None, now) is False


def test_is_fresh_across_day_boundary():
    # cached yesterday, checked just after midnight ET → stale (forces a refetch)
    cached_day = date(2026, 6, 4)
    just_after_midnight = datetime(2026, 6, 5, 0, 5, tzinfo=ET)
    assert api_cache.is_fresh(cached_day, just_after_midnight) is False


def test_resolve_mode_maps_session_phase(monkeypatch):
    cases = {
        "premarket": "preopen",
        "open": "intraday",
        "afterhours": "postclose",
        "closed": None,            # weekend/holiday → no-op
    }
    for phase, expected in cases.items():
        monkeypatch.setattr(calendar_utils, "session_phase", lambda *a, **k: phase)
        assert calendar_utils.resolve_mode() == expected
