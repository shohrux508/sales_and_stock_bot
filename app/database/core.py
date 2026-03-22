from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.config import settings

from sqlalchemy import MetaData

import os

# Construct SQLite URL. Alembic setup will use this or a similar connection string.
# Using check_same_thread=False for sqlite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///app.db")
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)
Base = declarative_base(metadata=metadata)

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
