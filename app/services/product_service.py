import logging
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.database.models import Product

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_all_products(self) -> Sequence[Product]:
        try:
            async with self.session_maker() as session:
                stmt = select(Product).options(selectinload(Product.category)).where(Product.is_active == 1).order_by(Product.name)
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError:
            logger.exception("DB error in get_all_products")
            return []

    async def get_product_by_id(self, product_id: int) -> Product | None:
        try:
            async with self.session_maker() as session:
                stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception(f"DB error in get_product_by_id({product_id})")
            return None

    async def get_products_by_category(self, category_id: int) -> Sequence[Product]:
        try:
            async with self.session_maker() as session:
                stmt = select(Product).options(selectinload(Product.category)).where(Product.category_id == category_id, Product.is_active == 1).order_by(Product.name)
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError:
            logger.exception(f"DB error in get_products_by_category({category_id})")
            return []

    async def create_product(self, name: str, price: float, quantity: int, category_id: int | None = None) -> Product:
        try:
            async with self.session_maker() as session:
                stmt = select(Product).where(Product.name == name)
                result = await session.execute(stmt)
                existing_product = result.scalar_one_or_none()

                if existing_product:
                    if existing_product.is_active == 1:
                        # Product exists and is active, let it raise or handle
                        raise ValueError(f"Product with name '{name}' already exists.")
                    else:
                        # Reactivate soft-deleted product
                        existing_product.is_active = 1
                        existing_product.price = price
                        existing_product.quantity = quantity
                        existing_product.category_id = category_id
                        await session.commit()
                        await session.refresh(existing_product)
                        return existing_product
                else:
                    product = Product(name=name, price=price, quantity=quantity, category_id=category_id)
                    session.add(product)
                    await session.commit()
                    await session.refresh(product)
                    return product
        except Exception:
            logger.exception(f"DB error in create_product({name})")
            raise

    async def update_quantity(self, product_id: int, quantity_delta: int) -> Product | None:
        try:
            async with self.session_maker() as session:
                # Atomic update to prevent race conditions
                stmt = (
                    update(Product)
                    .where(Product.id == product_id)
                    .values(quantity=Product.quantity + quantity_delta)
                    .returning(Product)
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                if product:
                    await session.commit()
                return product
        except SQLAlchemyError:
            logger.exception(f"DB error in update_quantity({product_id}, {quantity_delta})")
            return None

    async def update_barcode(self, product_id: int, barcode: str) -> bool:
        try:
            async with self.session_maker() as session:
                stmt = update(Product).where(Product.id == product_id).values(barcode=barcode)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except SQLAlchemyError:
            logger.exception(f"DB error in update_barcode({product_id})")
            return False

    async def get_product_by_barcode(self, barcode: str) -> Product | None:
        try:
            async with self.session_maker() as session:
                stmt = select(Product).options(selectinload(Product.category)).where(Product.barcode == barcode)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception(f"DB error in get_product_by_barcode({barcode})")
            return None

    async def delete_product(self, product_id: int) -> bool:
        try:
            async with self.session_maker() as session:
                stmt = update(Product).where(Product.id == product_id).values(is_active=0)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except SQLAlchemyError:
            logger.exception(f"DB error in delete_product({product_id})")
            return False
