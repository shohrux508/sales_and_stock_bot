import os
import pytest
import pytest_asyncio

# Set variable BEFORE any app import so that SQLAlchemy uses aiosqlite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["BOT_TOKEN"] = "123456789:ABCDEF"
os.environ["ADMIN_IDS"] = "123,456"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.core import Base, engine

@pytest_asyncio.fixture
async def db_engine():
    # Use the overridden engine or create a new one
    test_engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest_asyncio.fixture
async def async_session_maker(db_engine):
    # This fixture yields a sessionmaker
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    
    # We could seed base data here
    from app.database.models import User, Category, Product, UserRole
    async with maker() as session:
        user = User(tg_id=123, role=UserRole.ADMIN)
        category = Category(name="Test Category")
        session.add(user)
        session.add(category)
        await session.commit()
        await session.refresh(user)
        await session.refresh(category)
        
        product = Product(name="Test Product", price=100.0, category_id=category.id, quantity=10, barcode="123456")
        session.add(product)
        await session.commit()

    yield maker
    
    # Optional DB cleanup if needed, but since it's an in-memory db that drops on engine disposal, 
    # we can also truncate tables if we reuse the engine.
    # We will just yield it.
