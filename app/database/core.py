from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.config import settings

# Construct SQLite URL. Alembic setup will use this or a similar connection string.
# Using check_same_thread=False for sqlite.
engine = create_async_engine(
    "sqlite+aiosqlite:///app.db",
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
