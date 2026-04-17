import pytest
from unittest.mock import MagicMock
from app.telegram.keyboards.admin import products_list_kb, categories_list_kb
from app.telegram.keyboards.worker import sell_product_list_kb, worker_categories_kb

class MockItem:
    def __init__(self, id, name, quantity=10):
        self.id = id
        self.name = name
        self.quantity = quantity

def test_products_list_kb_pagination():
    # Create 25 products
    products = [MockItem(i, f"Product {i}") for i in range(25)]
    
    # Check first page
    kb = products_list_kb(products, page=0, page_size=20)
    buttons = []
    for row in kb.inline_keyboard:
        for btn in row:
            buttons.append(btn)
            
    # Should have 20 product buttons + 1 navigation button (Next) + 1 Add button
    # Actually builder.adjust(2) for products, then row(nav), then row(add)
    # Total buttons: 20 + 1 + 1 = 22
    assert len(buttons) == 22
    assert any(btn.text == "Keyingi ➡️" for btn in buttons)
    assert not any(btn.text == "⬅️ Oldingi" for btn in buttons)
    
    # Check second page
    kb = products_list_kb(products, page=1, page_size=20)
    buttons = []
    for row in kb.inline_keyboard:
        for btn in row:
            buttons.append(btn)
            
    # Should have 5 product buttons + 1 navigation button (Prev) + 1 Add button
    # Total buttons: 5 + 1 + 1 = 7
    assert len(buttons) == 7
    assert any(btn.text == "⬅️ Oldingi" for btn in buttons)
    assert not any(btn.text == "Keyingi ➡️" for btn in buttons)

def test_sell_product_list_kb_pagination():
    products = [MockItem(i, f"Product {i}") for i in range(25)]
    
    # Check first page
    kb = sell_product_list_kb(products, category_id=1, page=0, page_size=20)
    buttons = []
    for row in kb.inline_keyboard:
        for btn in row:
            buttons.append(btn)
            
    # 20 products + 1 nav (Next) + 2 footer (Back, Cancel)
    assert any(btn.text == "Keyingi ➡️" for btn in buttons)
    assert any(btn.text == "🔙 Qaytish" for btn in buttons)

def test_categories_list_kb_pagination():
    categories = [MockItem(i, f"Cat {i}") for i in range(25)]
    
    kb = categories_list_kb(categories, page=0, page_size=20)
    buttons = []
    for row in kb.inline_keyboard:
        for btn in row:
            buttons.append(btn)
            
    assert any(btn.text == "Keyingi ➡️" for btn in buttons)
    assert any(btn.text == "➕ Kategoriya yaratish" for btn in buttons)
