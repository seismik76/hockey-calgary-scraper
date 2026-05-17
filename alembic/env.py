import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Make the project root importable so we can pull in the models.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

from models import Base  # noqa: E402

config = context.config

# Override sqlalchemy.url from the environment so Alembic uses the same
# DATABASE_URL as the application (no need to maintain it in two places).
# We install psycopg3, not psycopg2 — force the driver if the URL doesn't
# specify one (Neon and most managed hosts return a plain `postgresql://`
# URL with no driver). Mirrors the same normalization in database.py.
db_url = os.environ.get("DATABASE_URL")
if db_url:
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg://" + db_url[len("postgresql://"):]
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
