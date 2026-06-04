"""Tiny forward-only migration runner. Applies migrations/*.sql in order once.

    python -m tracker.migrate

Tracks applied files in schema_migrations. Idempotent — safe to re-run.
"""
from __future__ import annotations

from pathlib import Path

from .config import load_env
from . import db

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def run() -> None:
    load_env()
    if not db.using_db():
        raise SystemExit("DATABASE_URL not set — nothing to migrate (file mode).")

    with db.connect() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        applied = {r["filename"] for r in c.execute("SELECT filename FROM schema_migrations").fetchall()}

        files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
        ran = 0
        for f in files:
            if f.name in applied:
                continue
            sql = f.read_text()
            c.execute(sql)
            c.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (f.name,))
            print(f"  applied {f.name}")
            ran += 1
    print(f"migrations: {ran} applied, {len(files)} total")


if __name__ == "__main__":
    run()
