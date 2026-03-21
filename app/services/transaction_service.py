from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from typing import Sequence
import logging
from datetime import datetime, timezone

from app.database.models import Transaction, Product, TransactionType

logger = logging.getLogger(__name__)

class TransactionService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def create_sale(self, user_id: int, product_id: int, amount: int, order_group_id: str | None = None) -> Transaction | None:
        """Records a sale and deduplicates stock within a single transaction. Returns None if stock is insufficient."""
        async with self.session_maker() as session:
            async with session.begin():
                # Lock row if needed, but for SQLite simple select is usually enough
                stmt = select(Product).where(Product.id == product_id)
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                
                if not product or product.quantity < amount:
                    return None
                
                # Deduct stock
                product.quantity -= amount
                
                # Create transaction
                total_price = product.price * amount
                transaction = Transaction(
                    user_id=user_id,
                    product_id=product_id,
                    amount=amount,
                    total_price=total_price,
                    type=TransactionType.SALE,
                    order_group_id=order_group_id,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None) # SQLite compatibility
                )
                
                session.add(transaction)
                await session.flush()
                # Ensure the relationships are loaded before closing
                await session.refresh(transaction, attribute_names=['product', 'user'])
                
            return transaction

    async def create_receipt(self, user_id: int, product_id: int, amount: int) -> Transaction | None:
        async with self.session_maker() as session:
            async with session.begin():
                stmt = select(Product).where(Product.id == product_id)
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                if not product:
                    return None
                    
                product.quantity += amount
                total_price = product.price * amount
                
                transaction = Transaction(
                    user_id=user_id,
                    product_id=product_id,
                    amount=amount,
                    total_price=total_price,
                    type=TransactionType.RECEIPT,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                session.add(transaction)
                await session.flush()
                await session.refresh(transaction, attribute_names=['product', 'user'])
            return transaction

    async def create_write_off(self, user_id: int, product_id: int, amount: int, reason: str) -> Transaction | None:
        async with self.session_maker() as session:
            async with session.begin():
                stmt = select(Product).where(Product.id == product_id)
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                if not product or product.quantity < amount:
                    return None
                    
                product.quantity -= amount
                total_price = product.price * amount
                
                transaction = Transaction(
                    user_id=user_id,
                    product_id=product_id,
                    amount=amount,
                    total_price=total_price,
                    type=TransactionType.WRITE_OFF,
                    reason=reason,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                session.add(transaction)
                await session.flush()
                await session.refresh(transaction, attribute_names=['product', 'user'])
            return transaction

    async def rollback_transaction(self, transaction_id: int) -> bool:
        async with self.session_maker() as session:
            stmt = select(Transaction).where(Transaction.id == transaction_id)
            result = await session.execute(stmt)
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                return False
                
            # Restore product quantity
            if transaction.product_id:
                prod_stmt = select(Product).where(Product.id == transaction.product_id)
                prod_result = await session.execute(prod_stmt)
                product = prod_result.scalar_one_or_none()
                if product:
                    if transaction.type == TransactionType.RECEIPT:
                        product.quantity -= transaction.amount
                    else: # SALE or WRITE_OFF
                        product.quantity += transaction.amount
                    
            # Delete transaction
            await session.delete(transaction)
            await session.commit()
            return True

    async def get_worker_sales_today(self, user_id: int) -> Sequence[Transaction]:
        """Gets all sales for a specific worker for the current day."""
        async with self.session_maker() as session:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Ensure relationships are loaded joining them
            from sqlalchemy.orm import selectinload
            stmt = select(Transaction).options(selectinload(Transaction.product)).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
                Transaction.timestamp >= today_start
            ).order_by(Transaction.timestamp.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_admin_statistics(self, period: str = "today") -> Sequence[Transaction]:
        """Gets all sales for administration depending on period (today or week)"""
        async with self.session_maker() as session:
            from datetime import timedelta
            now = datetime.now()
            
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) # fallback
                
            from sqlalchemy.orm import selectinload
            stmt = select(Transaction).options(
                selectinload(Transaction.product).selectinload(Product.category), 
                selectinload(Transaction.user)
            ).where(
                Transaction.type == TransactionType.SALE,
                Transaction.timestamp >= start_date
            ).order_by(Transaction.timestamp.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()
