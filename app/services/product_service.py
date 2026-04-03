from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update, delete
from typing import Sequence
import logging

from sqlalchemy.orm import selectinload

from app.database.models import Product

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_all_products(self) -> Sequence[Product]:
        async with self.session_maker() as session:
            stmt = select(Product).options(selectinload(Product.category)).where(Product.is_active == 1).order_by(Product.name)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_product_by_id(self, product_id: int) -> Product | None:
        async with self.session_maker() as session:
            stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
    async def get_products_by_category(self, category_id: int) -> Sequence[Product]:
        async with self.session_maker() as session:
            stmt = select(Product).options(selectinload(Product.category)).where(Product.category_id == category_id, Product.is_active == 1).order_by(Product.name)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_product(self, name: str, price: float, quantity: int, category_id: int | None = None) -> Product:
        async with self.session_maker() as session:
            product = Product(name=name, price=price, quantity=quantity, category_id=category_id)
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    async def update_quantity(self, product_id: int, quantity_delta: int) -> Product | None:
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

    async def update_barcode(self, product_id: int, barcode: str) -> bool:
        async with self.session_maker() as session:
            stmt = update(Product).where(Product.id == product_id).values(barcode=barcode)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_product_by_barcode(self, barcode: str) -> Product | None:
        async with self.session_maker() as session:
            stmt = select(Product).options(selectinload(Product.category)).where(Product.barcode == barcode)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_product(self, product_id: int) -> bool:
        async with self.session_maker() as session:
            stmt = update(Product).where(Product.id == product_id).values(is_active=0)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
