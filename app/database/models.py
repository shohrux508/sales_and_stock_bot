import enum
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core import Base

class UserRole(enum.Enum):
    ADMIN = "admin"
    WORKER = "worker"
    PENDING = "pending"
    BANNED = "banned"

class TransactionType(enum.Enum):
    SALE = "sale"
    RECEIPT = "receipt"
    WRITE_OFF = "write_off"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.WORKER)
    kpi: Mapped[int] = mapped_column(Integer, default=0)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active: Mapped[bool] = mapped_column(Integer, default=1) # 1 for True, 0 for False (SQLite compatibility)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user"
    )

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )

from decimal import Decimal
from sqlalchemy import BigInteger, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.0)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    barcode: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1) # 1 for True, 0 for False (SQLite compatibility)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="product"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), default=TransactionType.SALE)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_group_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    product: Mapped["Product"] = relationship("Product", back_populates="transactions")
