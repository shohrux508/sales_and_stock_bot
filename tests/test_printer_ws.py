"""
Тесты для WebSocket-менеджера принтеров (PrinterConnectionManager).

Тестирует:
- Подключение/отключение клиентов
- Отправку заданий на печать
- Дедупликацию order_id
- Очередь непечатанных чеков
- Повторную печать
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Устанавливаем тестовые переменные до импорта приложения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["BOT_TOKEN"] = "123456789:ABCDEF"
os.environ["ADMIN_IDS"] = "123,456"
os.environ["PRINTER_SECRET_TOKEN"] = "test-printer-token-123"

from app.api.printer_manager import PrinterConnectionManager


# --- Фикстуры ---

@pytest_asyncio.fixture
async def manager():
    """Свежий экземпляр PrinterConnectionManager для каждого теста."""
    m = PrinterConnectionManager()
    return m


def make_mock_ws():
    """Создает mock WebSocket с необходимыми методами."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


def make_order_data(order_id="ORD-001"):
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


# --- Тесты подключения ---

class TestConnection:
    
    @pytest.mark.asyncio
    async def test_connect_registers_client(self, manager):
        """Принтер подключается — должен зарегистрироваться в менеджере."""
        ws = make_mock_ws()
        await manager.connect(ws, "client-1")
        
        assert "client-1" in manager.active_connections
        assert manager.has_connected_printer is True
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self, manager):
        """Принтер отключается — должен удалиться из менеджера."""
        ws = make_mock_ws()
        await manager.connect(ws, "client-1")
        manager.disconnect("client-1")
        
        assert "client-1" not in manager.active_connections
        assert manager.has_connected_printer is False

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client(self, manager):
        """Отключение несуществующего клиента не вызывает ошибку."""
        manager.disconnect("nonexistent")  # должен не падать

    @pytest.mark.asyncio
    async def test_has_connected_printer_empty(self, manager):
        """Нет подключенных принтеров."""
        assert manager.has_connected_printer is False


# --- Тесты отправки заданий ---

class TestSendPrintJob:
    
    @pytest.mark.asyncio
    async def test_send_job_to_connected_printer(self, manager):
        """Чек отправляется подключенному принтеру."""
        ws = make_mock_ws()
        await manager.connect(ws, "client-1")
        
        order = make_order_data("ORD-100")
        result = await manager.send_print_job(order)
        
        assert result is True
        ws.send_json.assert_called_once_with(order)

    @pytest.mark.asyncio
    async def test_send_job_no_clients(self, manager):
        """Нет принтеров — чек уходит в очередь pending_jobs."""
        order = make_order_data("ORD-200")
        result = await manager.send_print_job(order)
        
        assert result is False
        assert len(manager.pending_jobs) == 1
        assert manager.pending_jobs[0]["order_id"] == "ORD-200"

    @pytest.mark.asyncio
    async def test_send_job_client_disconnected_during_send(self, manager):
        """Принтер отключается во время отправки — чек уходит в очередь."""
        ws = make_mock_ws()
        ws.send_json.side_effect = Exception("Connection lost")
        await manager.connect(ws, "client-broken")
        
        order = make_order_data("ORD-300")
        result = await manager.send_print_job(order)
        
        assert result is False
        assert "client-broken" not in manager.active_connections
        assert len(manager.pending_jobs) == 1


# --- Тесты дедупликации ---

class TestDeduplication:
    
    @pytest.mark.asyncio
    async def test_no_redis_no_dedup(self, manager):
        """Без Redis дедупликация отключена — is_duplicate всегда False."""
        result = await manager.is_duplicate("ORD-999")
        assert result is False

    @pytest.mark.asyncio
    async def test_mark_as_printed_without_redis(self, manager):
        """Без Redis _mark_as_printed не падает."""
        await manager._mark_as_printed("ORD-999")  # должен не падать


# --- Тесты очереди ---

class TestPendingQueue:
    
    @pytest.mark.asyncio
    async def test_add_to_pending(self, manager):
        """Чек добавляется в очередь."""
        order = make_order_data("ORD-400")
        manager._add_to_pending(order)
        
        assert len(manager.pending_jobs) == 1
        assert manager.pending_jobs[0]["order_id"] == "ORD-400"

    @pytest.mark.asyncio
    async def test_pending_max_size(self, manager):
        """Очередь не превышает максимальный размер (FIFO ротация)."""
        manager._max_pending = 3
        for i in range(5):
            manager._add_to_pending(make_order_data(f"ORD-{i}"))
        
        assert len(manager.pending_jobs) == 3
        # Должны остаться последние 3
        assert manager.pending_jobs[0]["order_id"] == "ORD-2"
        assert manager.pending_jobs[2]["order_id"] == "ORD-4"

    @pytest.mark.asyncio
    async def test_get_pending_job(self, manager):
        """Получение чека из очереди по order_id."""
        manager._add_to_pending(make_order_data("ORD-500"))
        manager._add_to_pending(make_order_data("ORD-501"))
        
        job = manager.get_pending_job("ORD-501")
        assert job is not None
        assert job["order_id"] == "ORD-501"

    @pytest.mark.asyncio
    async def test_get_pending_job_not_found(self, manager):
        """Чек не найден в очереди."""
        job = manager.get_pending_job("ORD-NONEXISTENT")
        assert job is None

    @pytest.mark.asyncio
    async def test_remove_pending_job(self, manager):
        """Удаление чека из очереди."""
        manager._add_to_pending(make_order_data("ORD-600"))
        
        result = manager.remove_pending_job("ORD-600")
        assert result is True
        assert len(manager.pending_jobs) == 0

    @pytest.mark.asyncio
    async def test_remove_pending_job_not_found(self, manager):
        """Удаление несуществующего чека — False."""
        result = manager.remove_pending_job("ORD-NONEXISTENT")
        assert result is False


# --- Тесты повторной печати ---

class TestRetryPrint:
    
    @pytest.mark.asyncio
    async def test_retry_no_printer(self, manager):
        """Повторная печать без принтера — False."""
        manager._add_to_pending(make_order_data("ORD-700"))
        
        result = await manager.retry_print_job("ORD-700")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_job_not_in_queue(self, manager):
        """Повторная печать чека, которого нет в очереди — False."""
        ws = make_mock_ws()
        await manager.connect(ws, "client-1")
        
        result = await manager.retry_print_job("ORD-NONEXISTENT")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_success(self, manager):
        """Успешная повторная печать — чек удаляется из очереди."""
        ws = make_mock_ws()
        await manager.connect(ws, "client-1")
        
        order = make_order_data("ORD-800")
        manager._add_to_pending(order)
        
        result = await manager.retry_print_job("ORD-800")
        
        assert result is True
        assert len(manager.pending_jobs) == 0
        ws.send_json.assert_called_once_with(order)
