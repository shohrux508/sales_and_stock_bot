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

    async def create_bulk_sale(self, user_id: int, items: list[dict], order_group_id: str) -> Sequence[Transaction] | None:
        """Records multiple sales atomically. Returns None if any item has insufficient stock."""
        async with self.session_maker() as session:
            async with session.begin():
                transactions = []
                for item in items:
                    product_id = item['product_id']
                    amount = item['amount']
                    
                    from sqlalchemy import update
                    stmt = update(Product).where(
                        Product.id == product_id, 
                        Product.quantity >= amount,
                        Product.is_active == 1
                    ).values(quantity=Product.quantity - amount).returning(Product)
                    
                    result = await session.execute(stmt)
                    product = result.scalar_one_or_none()
                    
                    if not product:
                        return None # Rolled back automatically
                    
                    total_price = product.price * amount
                    
                    tx = Transaction(
                        user_id=user_id,
                        product_id=product_id,
                        amount=amount,
                        total_price=total_price,
                        type=TransactionType.SALE,
                        order_group_id=order_group_id,
                        timestamp=datetime.now(timezone.utc)
                    )
                    session.add(tx)
                    transactions.append(tx)
                
                await session.flush()
                for tx in transactions:
                    await session.refresh(tx, attribute_names=['product', 'user'])
                return transactions

    async def create_sale(self, user_id: int, product_id: int, amount: int, order_group_id: str | None = None) -> Transaction | None:
        """Records a sale and deduplicates stock within a single transaction. Returns None if stock is insufficient."""
        async with self.session_maker() as session:
            async with session.begin():
                from sqlalchemy import update
                stmt = update(Product).where(
                    Product.id == product_id, 
                    Product.quantity >= amount,
                    Product.is_active == 1
                ).values(quantity=Product.quantity - amount).returning(Product)
                
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                
                if not product:
                    return None
                
                # Create transaction
                total_price = product.price * amount
                transaction = Transaction(
                    user_id=user_id,
                    product_id=product_id,
                    amount=amount,
                    total_price=total_price,
                    type=TransactionType.SALE,
                    order_group_id=order_group_id,
                    timestamp=datetime.now(timezone.utc)
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
                    timestamp=datetime.now(timezone.utc)
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
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(transaction)
                await session.flush()
                await session.refresh(transaction, attribute_names=['product', 'user'])
            return transaction

    async def rollback_transaction(self, transaction_id: int) -> bool:
        async with self.session_maker() as session:
            async with session.begin():
                # Get transaction with FOR UPDATE to prevent double rollback
                from sqlalchemy import select
                stmt = select(Transaction).where(Transaction.id == transaction_id).with_for_update()
                result = await session.execute(stmt)
                transaction = result.scalar_one_or_none()
                
                if not transaction:
                    return False
                    
                # Restore product quantity atomically
                if transaction.product_id:
                    from sqlalchemy import update
                    if transaction.type == TransactionType.RECEIPT:
                        # For a receipt, rollback means subtracting
                        delta = -transaction.amount
                    else:
                        # For sale or write_off, rollback means adding back
                        delta = transaction.amount
                        
                    prod_stmt = (
                        update(Product)
                        .where(Product.id == transaction.product_id)
                        .values(quantity=Product.quantity + delta)
                    )
                    await session.execute(prod_stmt)
                        
                # Delete transaction
                await session.delete(transaction)
                return True

    def _get_start_of_day_utc(self) -> datetime:
        """Returns UTC timestamp for the start of the day in Uzbekistan (UTC+5)."""
        from datetime import timedelta
        # Current time in UZT
        uzt_now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5)))
        # Start of today in UZT
        uzt_start = uzt_now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Back to UTC for DB filtering
        return uzt_start.astimezone(timezone.utc)

    async def get_worker_sales_today(self, user_id: int) -> Sequence[Transaction]:
        """Gets all sales for a specific worker for the current day based on UZT (+5) time."""
        async with self.session_maker() as session:
            today_start = self._get_start_of_day_utc()
            
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
            if period == "today":
                start_date = self._get_start_of_day_utc()
            else:
                from datetime import timedelta
                # Last 7 days in UZT
                uzt_now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5)))
                start_date = (uzt_now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

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
            now = datetime.now(timezone.utc)
            
            if period == "today":
                start_date = self._get_start_of_day_utc()
            elif period == "week":
                from datetime import timedelta
                uzt_now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5)))
                start_date = (uzt_now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            else:
                start_date = self._get_start_of_day_utc() # fallback
                
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
