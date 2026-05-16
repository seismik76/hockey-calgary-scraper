"""
Regenerate the SQLite seed file (data/seed/hockey_calgary.db) from the current
Postgres DB pointed at by DATABASE_URL.

Use this when the live DB is materially better than the existing seed — typically
after a successful scrape that picked up new sources, or after an `import_seed_data`
run that merged in older history. The seed becomes a movable checkpoint.

By default, the existing seed file is backed up with a timestamp suffix before
being replaced. Pass --no-backup to skip.

Usage:
    python scripts/maintenance/promote_to_seed.py
    python scripts/maintenance/promote_to_seed.py --dest data/seed/hockey_calgary.db --no-backup
"""
import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Season, Community, League, Team, Standing
from database import engine as src_engine


# Order matters: parents before children
EXPORT_ORDER = [Season, Community, League, Team, Standing]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', default='data/seed/hockey_calgary.db',
                        help='Destination SQLite file (default: data/seed/hockey_calgary.db)')
    parser.add_argument('--no-backup', action='store_true',
                        help='Do not back up the existing seed before overwriting.')
    args = parser.parse_args()

    dest_path = Path(args.dest).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Source:      {src_engine.url}")
    print(f"Destination: {dest_path}")

    # 1. Back up the existing seed
    if dest_path.exists() and not args.no_backup:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup = dest_path.with_name(f"{dest_path.stem}.{ts}.bak.db")
        shutil.copy2(dest_path, backup)
        print(f"Backed up existing seed to: {backup.name}")

    # 2. Delete the destination so we get a fresh copy (no stale rows lingering)
    if dest_path.exists():
        dest_path.unlink()

    # 3. Build schema in destination using the current ORM models
    dest_engine = create_engine(f"sqlite:///{dest_path}")
    Base.metadata.create_all(bind=dest_engine)

    SrcSession = sessionmaker(bind=src_engine)
    DestSession = sessionmaker(bind=dest_engine)
    src = SrcSession()
    dest = DestSession()

    total = 0
    try:
        for model in EXPORT_ORDER:
            rows = src.query(model).all()
            if not rows:
                print(f"  {model.__tablename__}: empty")
                continue
            cols = [c.name for c in model.__table__.columns]
            records = [{col: getattr(r, col) for col in cols} for r in rows]
            dest.execute(model.__table__.insert(), records)
            dest.commit()
            total += len(records)
            print(f"  {model.__tablename__}: copied {len(records)} rows")
    finally:
        src.close()
        dest.close()

    print(f"Done. Wrote {total} rows to {dest_path}")


if __name__ == '__main__':
    main()
