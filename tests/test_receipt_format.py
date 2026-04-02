"""
Тесты форматирования чеков (receipt_printer).

Тестирует:
- Корректность структуры текстового чека
- Обрезку длинных названий товаров
- Форматирование итоговой суммы
- Обработку пустых данных
"""

import os
import sys
import pytest

# Добавляем printer_client в path для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "printer_client"))

# Устанавливаем тестовые переменные до импорта приложения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["BOT_TOKEN"] = "123456789:ABCDEF"
os.environ["ADMIN_IDS"] = "123,456"


def make_order_data(order_id="ORD-TEST-001"):
    """Создает тестовые данные заказа."""
    return {
        "order_id": order_id,
        "timestamp": "2026-04-02 14:20:00",
        "worker_name": "Тестовый Сотрудник",
        "items": [
            {"name": "Товар 1", "quantity": 2, "price": 50000, "sum": 100000},
            {"name": "Товар 2", "quantity": 1, "price": 25000, "sum": 25000},
        ],
        "total_amount": 125000,
        "currency": "UZS",
    }


class TestReceiptDataStructure:
    """Тесты валидации JSON-структуры данных чека."""

    def test_order_data_has_required_fields(self):
        """JSON данные чека содержат все обязательные поля."""
        data = make_order_data()
        required_fields = ["order_id", "timestamp", "worker_name", "items", "total_amount", "currency"]
        for field in required_fields:
            assert field in data, f"Поле '{field}' отсутствует в данных чека"

    def test_order_items_structure(self):
        """Каждый товар содержит name, quantity, price, sum."""
        data = make_order_data()
        for item in data["items"]:
            assert "name" in item
            assert "quantity" in item
            assert "price" in item
            assert "sum" in item

    def test_total_amount_matches_items_sum(self):
        """Итого совпадает с суммой всех позиций."""
        data = make_order_data()
        items_total = sum(item["sum"] for item in data["items"])
        assert data["total_amount"] == items_total

    def test_item_sum_equals_price_times_quantity(self):
        """sum каждого товара равен price * quantity."""
        data = make_order_data()
        for item in data["items"]:
            assert item["sum"] == item["price"] * item["quantity"]


class TestReceiptFormatting:
    """Тесты форматирования текстового чека."""

    def test_format_receipt_contains_shop_name(self):
        """Чек содержит название магазина."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert "Sale & Stock Bot" in text

    def test_format_receipt_contains_order_id(self):
        """Чек содержит номер заказа."""
        from receipt_printer import format_receipt_text
        data = make_order_data("ORD-99999")
        text = format_receipt_text(data)
        assert "ORD-99999" in text

    def test_format_receipt_contains_worker_name(self):
        """Чек содержит имя сотрудника."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert data["worker_name"] in text

    def test_format_receipt_contains_total(self):
        """Чек содержит итоговую сумму."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert "JAMI:" in text
        assert "125,000" in text

    def test_format_receipt_contains_currency(self):
        """Чек содержит валюту."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert "UZS" in text

    def test_format_receipt_contains_thank_you(self):
        """Чек содержит благодарственное сообщение."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert "Rahmat" in text
        assert "minnatdormiz" in text

    def test_format_receipt_contains_timestamp(self):
        """Чек содержит дату/время."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        assert data["timestamp"] in text

    def test_format_receipt_items_listed(self):
        """Чек содержит все товары."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        text = format_receipt_text(data)
        for item in data["items"]:
            assert item["name"] in text


class TestReceiptEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_items_list(self):
        """Чек с пустым списком товаров."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        data["items"] = []
        data["total_amount"] = 0
        text = format_receipt_text(data)
        assert "JAMI:" in text

    def test_long_product_name_truncated(self):
        """Длинное название товара обрезается."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        data["items"] = [
            {"name": "Очень длинное название товара которое не влезает в строку", "quantity": 1, "price": 1000, "sum": 1000}
        ]
        text = format_receipt_text(data)
        # Текст не должен содержать полного названия (32 символа ширина)
        lines = text.split("\n")
        for line in lines:
            assert len(line) <= 32, f"Строка слишком длинная ({len(line)}): '{line}'"

    def test_cyrillic_characters(self):
        """Чек корректно содержит кириллицу."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        data["worker_name"] = "Иванов Иван"
        data["items"] = [{"name": "Молоко", "quantity": 1, "price": 5000, "sum": 5000}]
        data["total_amount"] = 5000
        text = format_receipt_text(data)
        assert "Иванов Иван" in text
        assert "Молоко" in text

    def test_uzbek_latin_characters(self):
        """Чек корректно содержит узбекскую латиницу."""
        from receipt_printer import format_receipt_text
        data = make_order_data()
        data["worker_name"] = "Shohrux Yigitaliyev"
        data["items"] = [{"name": "Non", "quantity": 3, "price": 3000, "sum": 9000}]
        data["total_amount"] = 9000
        text = format_receipt_text(data)
        assert "Shohrux" in text
        assert "Non" in text
