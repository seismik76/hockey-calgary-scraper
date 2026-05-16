import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base  # noqa: F401  (imported so Alembic env can pick up models)

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env (or export the variable) "
        "and point it at your local Postgres instance — see docker-compose.yml."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
# expire_on_commit=False prevents SQLAlchemy from invalidating instance attributes
# after commit. Without it, every attribute access after commit reopens a transaction
# to reload the row, which keeps Postgres sessions stuck in "idle in transaction".
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)


def init_db():
    """Apply any pending Alembic migrations. Idempotent — a DB already at head is a no-op."""
    from alembic.config import Config
    from alembic import command

    project_root = Path(__file__).resolve().parent
    cfg = Config(str(project_root / "alembic.ini"))
    # alembic/env.py reads DATABASE_URL itself, but we set it here too for completeness.
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
