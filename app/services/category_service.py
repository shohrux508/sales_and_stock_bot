from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from typing import Sequence
import logging

from app.database.models import Category, Product

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

    async def count_products_in_category(self, category_id: int) -> int:
        async with self.session_maker() as session:
            stmt = select(func.count()).select_from(Product).where(Product.category_id == category_id)
            return int((await session.execute(stmt)).scalar_one() or 0)

    async def rename_category(self, category_id: int, name: str) -> Category | None:
        name = name.strip()
        if not name:
            return None
        async with self.session_maker() as session:
            cat = await session.get(Category, category_id)
            if not cat:
                return None
            cat.name = name
            try:
                await session.commit()
                await session.refresh(cat)
                return cat
            except IntegrityError:
                await session.rollback()
                raise

    async def delete_category(self, category_id: int) -> bool:
        """Deletes category and unlinks products (sets their category_id to NULL)."""
        async with self.session_maker() as session:
            cat = await session.get(Category, category_id)
            if not cat:
                return False
            
            # Unlink products instead of deleting them or blocking
            from sqlalchemy import update
            await session.execute(
                update(Product).where(Product.category_id == category_id).values(category_id=None)
            )
            
            await session.delete(cat)
            await session.commit()
            return True
