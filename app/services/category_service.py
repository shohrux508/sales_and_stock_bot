import logging
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.models import Category, Product

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_all_categories(self) -> Sequence[Category]:
        try:
            async with self.session_maker() as session:
                stmt = select(Category).order_by(Category.name)
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError:
            logger.exception("DB error in get_all_categories")
            return []

    async def get_category_by_id(self, category_id: int) -> Category | None:
        try:
            async with self.session_maker() as session:
                stmt = select(Category).where(Category.id == category_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception(f"DB error in get_category_by_id({category_id})")
            return None

    async def create_category(self, name: str) -> Category:
        try:
            async with self.session_maker() as session:
                category = Category(name=name)
                session.add(category)
                await session.commit()
                await session.refresh(category)
                return category
        except SQLAlchemyError:
            logger.exception(f"DB error in create_category({name})")
            raise

    async def count_products_in_category(self, category_id: int) -> int:
        try:
            async with self.session_maker() as session:
                stmt = select(func.count()).select_from(Product).where(Product.category_id == category_id)
                return int((await session.execute(stmt)).scalar_one() or 0)
        except SQLAlchemyError:
            logger.exception(f"DB error in count_products_in_category({category_id})")
            return 0

    async def rename_category(self, category_id: int, name: str) -> Category | None:
        name = name.strip()
        if not name:
            return None
        try:
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
        except IntegrityError:
            raise
        except SQLAlchemyError:
            logger.exception(f"DB error in rename_category({category_id}, {name})")
            return None

    async def delete_category(self, category_id: int) -> bool:
        """Deletes category and unlinks products (sets their category_id to NULL)."""
        try:
            async with self.session_maker() as session:
                cat = await session.get(Category, category_id)
                if not cat:
                    return False

                # Unlink products instead of deleting them or blocking
                await session.execute(
                    update(Product).where(Product.category_id == category_id).values(category_id=None)
                )

                await session.delete(cat)
                await session.commit()
                return True
        except SQLAlchemyError:
            logger.exception(f"DB error in delete_category({category_id})")
            return False
