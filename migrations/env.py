import asyncio
import logging
import os
from dotenv import load_dotenv
from logging.config import fileConfig

load_dotenv()

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# add your model's MetaData object here
# for 'autogenerate' support
from app.database.core import Base
import app.database.models  # Ensure models are imported for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url with our URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///app.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Explicitly set version_locations so Alembic always resolves migration files
# relative to this env.py, regardless of the working directory.
_here = os.path.dirname(os.path.abspath(__file__))
_versions_dir = os.path.join(_here, "versions")
config.set_main_option("version_locations", _versions_dir)
logger.info("Alembic version_locations set to: %s", _versions_dir)
logger.info("Alembic sqlalchemy.url driver: %s", DATABASE_URL.split("://")[0])


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
            break  # Break out of loop on success
        except Exception as e:
            error_message = str(e) + " " + str(getattr(e, 'orig', ''))
            if "database system is starting up" in error_message and attempt < max_retries - 1:
                print(f"Database is starting up, retrying in 3 seconds... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(3)
            else:
                raise

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
