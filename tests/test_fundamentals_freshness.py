from datetime import date, datetime, timedelta, timezone

from tracker.quarterly import is_stale, record_from_quarters, Quarter

NOW = datetime(2026, 6, 5, tzinfo=timezone.utc)


def dt(days_ago):
    return NOW - timedelta(days=days_ago)


def test_no_data_is_stale():
    assert is_stale(None, None, None, NOW) is True
    assert is_stale(date(2026, 3, 31), None, None, NOW) is True  # no fetched_at


def test_current_quarter_is_fresh():
    # reported 2026-03-31, announced ~40 days later, fetched recently
    assert is_stale(date(2026, 3, 31), dt(2), date(2026, 5, 10), NOW) is False


def test_newer_quarter_reported_is_stale():
    # we hold Q ending 2025-12-31 but a report landed 2026-05-01 (~120d later) -> behind
    assert is_stale(date(2025, 12, 31), dt(1), date(2026, 5, 1), NOW) is True


def test_time_backstop_triggers_when_old():
    # within the cycle window, but our fetch is ancient -> stale (catches restatements)
    assert is_stale(date(2026, 3, 31), dt(30), date(2026, 5, 10), NOW, max_age_days=7) is True


def test_no_last_date_relies_on_backstop():
    assert is_stale(date(2026, 3, 31), dt(2), None, NOW) is False
    assert is_stale(date(2026, 3, 31), dt(30), None, NOW, max_age_days=7) is True


def test_record_from_quarters_has_fields():
    qs = [
        Quarter(date(2026, 4, 30), revenue=7910e6, eps=3.51, gross_profit=3947e6),
        Quarter(date(2026, 1, 31), revenue=7012e6, eps=2.54, gross_profit=3435e6),
    ]
    rec = record_from_quarters(qs)
    assert rec["report_date"] == date(2026, 4, 30)
    assert rec["revenue_qoq_pct"] == round((7910 / 7012 - 1) * 100, 2)
    assert rec["gross_margin_qoq_pp"] is not None
    assert rec["revenue_yoy"] is None  # only 2 quarters -> YoY insufficient


def test_record_from_empty():
    assert record_from_quarters([]) is None
