from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, delete
from typing import Sequence
import logging

from app.database.models import Category

logger = logging.getLogger(__name__)

class CategoryService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_all_categories(self) -> Sequence[Category]:
        async with self.session_maker() as session:
            stmt = select(Category).order_by(Category.name)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_category_by_id(self, category_id: int) -> Category | None:
        async with self.session_maker() as session:
            stmt = select(Category).where(Category.id == category_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
    async def create_category(self, name: str) -> Category:
        async with self.session_maker() as session:
            category = Category(name=name)
            session.add(category)
            await session.commit()
            await session.refresh(category)
            return category

    async def delete_category(self, category_id: int) -> bool:
        async with self.session_maker() as session:
            stmt = delete(Category).where(Category.id == category_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
