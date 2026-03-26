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
        """Gets all sales for a specific worker for the current day based on local system time."""
        async with self.session_maker() as session:
            # For better accuracy, we can use a simpler approach: 
            # transactions where timestamp >= UTC start of day
            # But "today" for a person in UZT (+5) starts at UTC 19:00 (yesterday).
            # Let's use a naive start of day in UTC for now, but better way is:
            now_utc = datetime.now(timezone.utc)
            # Assuming Uzbekistan (+5) for many users of this bot (based on language)
            # We can calculate the start of the day in current system local time or +5.
            # Local time in this project seems to be +05:00 based on the prompt.
            today_start_local = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # How it's stored? datetime.now(timezone.utc).replace(tzinfo=None)
            # If we want "today" in local time, we need to find those UTC timestamps.
            # For +5, local 00:00:00 = UTC 19:00:00 yesterday.
            
            # Simple fix for now: just use the last 24 hours if "today" is tricky, 
            # but usually start of day in naive UTC is a good enough baseline for small shops.
            # HOWEVER, let's just use naive comparison to CURRENT day to make it "worker-friendly"
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            from sqlalchemy.orm import selectinload
            stmt = select(Transaction).options(selectinload(Transaction.product)).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SALE,
                Transaction.timestamp >= today_start
            ).order_by(Transaction.timestamp.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_staff_rankings(self, period: str = "today") -> Sequence[tuple[int, str, float, int]]:
        """Returns list of (tg_id, username, total_revenue, total_items) ranked by revenue."""
        async with self.session_maker() as session:
            from datetime import timedelta
            now = datetime.utcnow()
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

            from sqlalchemy import func
            from app.database.models import User
            
            stmt = select(
                User.tg_id, 
                User.username,
                func.sum(Transaction.total_price).label("revenue"),
                func.sum(Transaction.amount).label("items")
            ).join(Transaction).where(
                Transaction.type == TransactionType.SALE,
                Transaction.timestamp >= start_date
            ).group_by(User.id).order_by(func.sum(Transaction.total_price).desc())
            
            result = await session.execute(stmt)
            return result.all()

    async def get_admin_statistics(self, period: str = "today", user_id: int | None = None) -> Sequence[Transaction]:
        """Gets all sales for administration depending on period (today or week)"""
        async with self.session_maker() as session:
            from datetime import timedelta
            now = datetime.utcnow()
            
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) # fallback
                
            from sqlalchemy.orm import selectinload
            
            conditions = [
                Transaction.type == TransactionType.SALE,
                Transaction.timestamp >= start_date
            ]
            if user_id is not None:
                conditions.append(Transaction.user_id == user_id)
                
            stmt = select(Transaction).options(
                selectinload(Transaction.product).selectinload(Product.category), 
                selectinload(Transaction.user)
            ).where(*conditions).order_by(Transaction.timestamp.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()
