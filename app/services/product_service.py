from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update, delete
from typing import Sequence
import logging

from app.database.models import Product

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_all_products(self) -> Sequence[Product]:
        async with self.session_maker() as session:
            stmt = select(Product).order_by(Product.name)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_product_by_id(self, product_id: int) -> Product | None:
        async with self.session_maker() as session:
            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
    async def create_product(self, name: str, price: float, quantity: int) -> Product:
        async with self.session_maker() as session:
            product = Product(name=name, price=price, quantity=quantity)
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    async def update_quantity(self, product_id: int, quantity_delta: int) -> Product | None:
        async with self.session_maker() as session:
            # We can use update with returning or select then update
            product = await self.get_product_by_id(product_id)
            if not product:
                return None
            
            new_qty = product.quantity + quantity_delta
            stmt = update(Product).where(Product.id == product_id).values(quantity=new_qty).returning(Product)
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def delete_product(self, product_id: int) -> bool:
        async with self.session_maker() as session:
            stmt = delete(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
