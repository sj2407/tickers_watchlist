"""P1 gate: average-cost position math — Python reference (unit, always runs) and
the SQL view (integration, asserts the view reproduces the reference row-for-row).

MERGE RULE (plan P1): P1 may not merge unless the integration tests ACTUALLY ran:
    TEST_DATABASE_URL=postgresql://watchlist:watchlist@localhost:5433/watchlist \
        pytest -m integration tests/test_positions_view.py -ra
The sentinel test fails (not skips) when TEST_DATABASE_URL is set but unusable.
"""
from __future__ import annotations

import os

import pytest

from tracker.positions import Txn, fold

# ── shared scenario matrix (one source for unit AND integration) ───────────
# (name, txns, expected {shares, avg_cost, invested, realized_pl})
SCENARIOS = [
    ("buy_only",
     [Txn("buy", 10, 100, 1), Txn("buy", 5, 110, 1)],
     {"shares": 15, "avg_cost": 1552 / 15, "invested": 1552.0, "realized_pl": 0.0}),

    ("partial_sell_keeps_avg",
     [Txn("buy", 10, 100), Txn("sell", 5, 150)],
     {"shares": 5, "avg_cost": 100.0, "invested": 500.0, "realized_pl": 250.0}),

    # THE bug case: the 0001 view said avg 133.33 here (all-time buys average).
    ("sell_then_rebuy",
     [Txn("buy", 10, 100), Txn("sell", 5, 150), Txn("buy", 5, 200)],
     {"shares": 10, "avg_cost": 150.0, "invested": 1500.0, "realized_pl": 250.0}),

    # Full exit must RESET the average; the 0001 view blended to 150 here.
    ("full_exit_then_rebuy",
     [Txn("buy", 10, 100), Txn("sell", 10, 150), Txn("buy", 10, 200)],
     {"shares": 10, "avg_cost": 200.0, "invested": 2000.0, "realized_pl": 500.0}),

    ("fees_both_sides",
     [Txn("buy", 10, 100, 5), Txn("sell", 5, 150, 2)],
     {"shares": 5, "avg_cost": 100.5, "invested": 502.5, "realized_pl": 245.5}),

    ("sell_before_any_buy",
     [Txn("sell", 5, 100, 1)],
     {"shares": 0, "avg_cost": None, "invested": 0.0, "realized_pl": -1.0}),

    ("oversell_clamps_never_negative",
     [Txn("buy", 5, 100), Txn("sell", 10, 120, 1)],
     {"shares": 0, "avg_cost": None, "invested": 0.0, "realized_pl": 99.0}),

    ("same_timestamp_ordered_by_id",
     [Txn("buy", 10, 100), Txn("sell", 10, 150), Txn("buy", 5, 200)],
     {"shares": 5, "avg_cost": 200.0, "invested": 1000.0, "realized_pl": 500.0}),
]


def _assert_position(got: dict, want: dict):
    assert got["shares"] == pytest.approx(want["shares"])
    if want["avg_cost"] is None:
        assert got["avg_cost"] is None
    else:
        assert got["avg_cost"] == pytest.approx(want["avg_cost"])
    assert got["invested"] == pytest.approx(want["invested"])
    assert got["realized_pl"] == pytest.approx(want["realized_pl"])


# ── unit: the Python reference fold ────────────────────────────────────────

@pytest.mark.parametrize("name,txns,want", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_reference_fold(name, txns, want):
    _assert_position(fold(txns), want)


def test_realized_pl_is_order_dependent_unlike_the_old_view():
    # The 0001 view priced every sell at the FINAL overall average (retroactive).
    # The fold prices each sell at the average AT SALE TIME: a later expensive buy
    # must not change realized P/L that already happened.
    early_sell = fold([Txn("buy", 10, 100), Txn("sell", 5, 150), Txn("buy", 5, 300)])
    assert early_sell["realized_pl"] == pytest.approx(250.0)  # 5*(150-100), regardless of the 300 buy


# ── integration: the SQL view must equal the reference ─────────────────────

TEST_DB = os.environ.get("TEST_DATABASE_URL")


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(TEST_DB, row_factory=dict_row)


@pytest.fixture(scope="module")
def view_schema():
    """Throwaway schema with ALL migrations applied in order."""
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL not set (P1 merge gate requires this to RUN)")
    from pathlib import Path

    conn = _connect()
    conn.execute("DROP SCHEMA IF EXISTS p1_test CASCADE")
    conn.execute("CREATE SCHEMA p1_test")
    conn.execute("SET search_path TO p1_test")
    for f in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
        conn.execute(f.read_text())
    conn.commit()
    yield conn
    conn.execute("DROP SCHEMA IF EXISTS p1_test CASCADE")
    conn.commit()
    conn.close()


@pytest.mark.integration
def test_sentinel_db_reachable_when_configured():
    """FAILS (not skips) when TEST_DATABASE_URL is set but unusable — guards the
    merge gate against silently green skipped-integration runs."""
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL not set")
    conn = _connect()
    assert conn.execute("SELECT 1").fetchone() is not None
    conn.close()


@pytest.mark.integration
@pytest.mark.parametrize("name,txns,want", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_sql_view_matches_reference(view_schema, name, txns, want):
    conn = view_schema
    conn.execute("SET search_path TO p1_test")
    conn.execute("DELETE FROM transactions")
    # Same executed_at for every row: ordering must come from id (insertion order).
    for t in txns:
        conn.execute(
            "INSERT INTO transactions (ticker, side, shares, price, fees, executed_at) "
            "VALUES ('TST', %s, %s, %s, %s, '2026-06-09T12:00:00Z')",
            (t.side, t.shares, t.price, t.fees),
        )
    row = conn.execute("SELECT * FROM current_positions WHERE ticker = 'TST'").fetchone()
    conn.commit()
    assert row is not None
    _assert_position(row, want)
    _assert_position(fold(txns), want)  # and the reference agrees on the same data


@pytest.mark.integration
def test_view_columns_unchanged(view_schema):
    conn = view_schema
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'p1_test' AND table_name = 'current_positions' "
        "ORDER BY ordinal_position"
    ).fetchall()
    assert [r["column_name"] for r in rows] == [
        "ticker", "shares", "avg_cost", "invested", "realized_pl",
    ]
