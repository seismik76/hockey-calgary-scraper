"""One-shot migration from the local Postgres into Neon.

Pulls credentials from .env (DATABASE_URL for local, NEON_DIRECT for Neon —
the latter is normally commented out so it doesn't accidentally get used by
the app). Idempotent: every INSERT is `ON CONFLICT DO NOTHING`, so re-running
top-up the destination without disturbing existing rows.

Workflow:
  1. Apply Alembic migrations against Neon (creates any missing tables).
  2. Copy rows from each table in FK-safe order. Preserves source IDs so the
     existing FKs on the destination keep pointing at the right rows.
  3. Bump each sequence past the largest copied id so subsequent inserts on
     Neon don't collide.

Run:
    python -m scripts.migrate_to_neon
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

LOCAL_URL = os.environ.get("DATABASE_URL")
if not LOCAL_URL:
    sys.exit("DATABASE_URL not set")


def _read_neon_url() -> str:
    """NEON_DIRECT is intentionally commented in .env so dotenv won't load it."""
    for raw in (PROJECT_ROOT / ".env").read_text().splitlines():
        line = raw.lstrip("# \t")
        m = re.match(r"NEON_DIRECT\s*=\s*(.+)", line)
        if m:
            return m.group(1).strip()
    sys.exit("NEON_DIRECT not found in .env")


def _force_psycopg3(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


NEON_URL = _force_psycopg3(_read_neon_url())
LOCAL_URL = _force_psycopg3(LOCAL_URL)

# Order matters for FKs: parents first.
TABLES = [
    "communities",
    "seasons",
    "leagues",
    "teams",
    "standings",
    "games",
    "scrape_runs",
]


def run_alembic_against_neon() -> None:
    print("==> applying alembic migrations on Neon...")
    env = os.environ.copy()
    env["DATABASE_URL"] = NEON_URL
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit("alembic upgrade failed")


def copy_table(src, dst, table: str) -> int:
    cols = [
        r[0]
        for r in src.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t "
                "ORDER BY ordinal_position"
            ),
            {"t": table},
        ).fetchall()
    ]
    if not cols:
        print(f"  {table}: no columns found, skipping")
        return 0

    col_list = ", ".join(f'"{c}"' for c in cols)
    rows = src.execute(text(f'SELECT {col_list} FROM "{table}"')).fetchall()
    if not rows:
        print(f"  {table}: source empty, skipping")
        return 0

    placeholders = ", ".join(f":{c}" for c in cols)
    stmt = text(
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
        f"ON CONFLICT DO NOTHING"
    )

    inserted = 0
    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = [dict(zip(cols, r)) for r in rows[i:i + BATCH]]
        result = dst.execute(stmt, batch)
        inserted += result.rowcount or 0
    dst.commit()
    print(f"  {table}: copied {inserted} of {len(rows)} rows")

    # Bump the id sequence if this table has one.
    seq_row = dst.execute(
        text(
            "SELECT pg_get_serial_sequence(:t, 'id')"
        ),
        {"t": table},
    ).fetchone()
    seq = seq_row[0] if seq_row else None
    if seq:
        max_id = dst.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table}"')).scalar()
        dst.execute(text("SELECT setval(:s, :v, true)"), {"s": seq, "v": max(max_id, 1)})
        dst.commit()

    return inserted


def main() -> None:
    run_alembic_against_neon()

    src_engine = create_engine(LOCAL_URL)
    dst_engine = create_engine(NEON_URL)

    print("==> copying data...")
    with src_engine.connect() as src, dst_engine.connect() as dst:
        for table in TABLES:
            copy_table(src, dst, table)

    print("==> done. summary on Neon:")
    with dst_engine.connect() as dst:
        for table in TABLES:
            n = dst.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            print(f"  {table}: {n}")


if __name__ == "__main__":
    main()
