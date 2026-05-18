"""
One-time migration: copy data from the SQLite seed DB into the Postgres DB
pointed at by DATABASE_URL.

Usage:
    docker compose up -d      # ensure Postgres is running
    python scripts/maintenance/migrate_sqlite_to_postgres.py

By default reads from data/seed/hockey_calgary.db. Override with --source.
"""
import argparse
import os
import sys
from pathlib import Path

# Make the repo root importable when this script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import Base, Season, Community, League, Team, Standing
from database import engine as dest_engine


# Order matters: parents before children.
MIGRATION_ORDER = [Season, Community, League, Team, Standing]


def copy_table(model, src_session, dest_session, batch_size=500):
    rows = src_session.query(model).all()
    if not rows:
        print(f"  {model.__tablename__}: empty, skipping")
        return 0

    # Detach from source session and re-attach to dest by building plain dicts.
    columns = [c.name for c in model.__table__.columns]
    records = [{col: getattr(r, col) for col in columns} for r in rows]

    dest_session.execute(model.__table__.insert(), records)
    dest_session.commit()
    print(f"  {model.__tablename__}: copied {len(records)} rows")
    return len(records)


def reset_sequence(dest_session, table_name, pk='id'):
    """Postgres only: after explicit-id inserts, bump the sequence past MAX(id)."""
    dialect = dest_session.bind.dialect.name
    if dialect != 'postgresql':
        return
    seq = f"{table_name}_{pk}_seq"
    dest_session.execute(text(
        f"SELECT setval('{seq}', COALESCE((SELECT MAX({pk}) FROM {table_name}), 1))"
    ))
    dest_session.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--source',
        default='data/seed/hockey_calgary.db',
        help='Path to the source SQLite database file.',
    )
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop all destination tables before copying. Destructive!',
    )
    args = parser.parse_args()

    src_path = Path(args.source).resolve()
    if not src_path.exists():
        print(f"Source SQLite DB not found: {src_path}")
        sys.exit(1)

    src_engine = create_engine(f"sqlite:///{src_path}")
    SrcSession = sessionmaker(bind=src_engine)
    DestSession = sessionmaker(bind=dest_engine)

    print(f"Source:      {src_path}")
    print(f"Destination: {dest_engine.url}")

    if args.drop_existing:
        print("Dropping destination tables...")
        Base.metadata.drop_all(bind=dest_engine)

    print("Creating destination schema...")
    Base.metadata.create_all(bind=dest_engine)

    src = SrcSession()
    dest = DestSession()
    total = 0
    try:
        for model in MIGRATION_ORDER:
            total += copy_table(model, src, dest)
            reset_sequence(dest, model.__tablename__)
    finally:
        src.close()
        dest.close()

    print(f"Done. Copied {total} rows total.")


if __name__ == '__main__':
    main()
