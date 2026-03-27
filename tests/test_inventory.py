import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.models import Base, User, Product, Category, Transaction, TransactionType, UserRole
from app.services.transaction_service import TransactionService
from app.services.product_service import ProductService



@pytest.mark.asyncio
async def test_create_receipt(async_session_maker):
    tx_service = TransactionService(async_session_maker)
    prod_service = ProductService(async_session_maker)
    
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 10
    
    tx = await tx_service.create_receipt(user_id=1, product_id=1, amount=5)
    
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 15
    assert tx.type == TransactionType.RECEIPT
    assert tx.amount == 5

@pytest.mark.asyncio
async def test_create_write_off(async_session_maker):
    tx_service = TransactionService(async_session_maker)
    prod_service = ProductService(async_session_maker)
    
    tx = await tx_service.create_write_off(user_id=1, product_id=1, amount=2, reason="Broken")
    
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 8
    assert tx.type == TransactionType.WRITE_OFF
    assert tx.reason == "Broken"

@pytest.mark.asyncio
async def test_create_sale_with_order_group(async_session_maker):
    tx_service = TransactionService(async_session_maker)
    prod_service = ProductService(async_session_maker)
    
    tx1 = await tx_service.create_sale(user_id=1, product_id=1, amount=3, order_group_id="group-123")
    
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 7
    assert tx1.order_group_id == "group-123"
    assert tx1.type == TransactionType.SALE
    
@pytest.mark.asyncio
async def test_rollback_transaction(async_session_maker):
    tx_service = TransactionService(async_session_maker)
    prod_service = ProductService(async_session_maker)
    
    # Write off 2 items
    tx = await tx_service.create_write_off(user_id=1, product_id=1, amount=2, reason="Broken")
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 8
    
    # Rollback
    await tx_service.rollback_transaction(tx.id)
    product = await prod_service.get_product_by_id(1)
    assert product.quantity == 10  # quantity restored
