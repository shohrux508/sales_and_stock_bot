"""
Тесты для WebSocket-менеджера принтеров (PrinterConnectionManager).

Тестирует:
- Подключение/отключение клиентов
- Отправку заданий на печать
- Дедупликацию order_id
- Очередь непечатанных чеков (Redis-backed)
- Повторную печать
"""

import json
import os

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

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


@pytest_asyncio.fixture
async def manager_with_redis():
    """PrinterConnectionManager с замоканным Redis для тестов очереди."""
    m = PrinterConnectionManager()
    # Мокаем Redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.set = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=[])
    mock_redis.rpush = AsyncMock()
    mock_redis.ltrim = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.lrem = AsyncMock()
    m._redis = mock_redis
    m._redis_available = True
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
        """Нет принтеров — возвращается False (чек уходит в Redis-очередь)."""
        order = make_order_data("ORD-200")
        result = await manager.send_print_job(order)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_job_client_disconnected_during_send(self, manager):
        """Принтер отключается во время отправки — клиент удаляется."""
        ws = make_mock_ws()
        ws.send_json.side_effect = Exception("Connection lost")
        await manager.connect(ws, "client-broken")

        order = make_order_data("ORD-300")
        result = await manager.send_print_job(order)

        assert result is False
        assert "client-broken" not in manager.active_connections


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


# --- Тесты очереди (с замоканным Redis) ---

class TestPendingQueue:

    @pytest.mark.asyncio
    async def test_add_to_pending(self, manager_with_redis):
        """Чек добавляется в очередь Redis."""
        order = make_order_data("ORD-400")
        await manager_with_redis._add_to_pending(order)

        manager_with_redis._redis.rpush.assert_called_once()
        manager_with_redis._redis.ltrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_without_redis(self, manager):
        """Без Redis _add_to_pending просто no-op."""
        order = make_order_data("ORD-401")
        await manager._add_to_pending(order)  # не должен падать

    @pytest.mark.asyncio
    async def test_get_pending_job(self, manager_with_redis):
        """Получение чека из очереди по order_id."""
        order = make_order_data("ORD-500")
        manager_with_redis._redis.lrange.return_value = [json.dumps(order)]

        job = await manager_with_redis.get_pending_job("ORD-500")
        assert job is not None
        assert job["order_id"] == "ORD-500"

    @pytest.mark.asyncio
    async def test_get_pending_job_not_found(self, manager_with_redis):
        """Чек не найден в очереди."""
        manager_with_redis._redis.lrange.return_value = []
        job = await manager_with_redis.get_pending_job("ORD-NONEXISTENT")
        assert job is None

    @pytest.mark.asyncio
    async def test_remove_pending_job(self, manager_with_redis):
        """Удаление чека из очереди."""
        order = make_order_data("ORD-600")
        manager_with_redis._redis.lrange.return_value = [json.dumps(order)]

        result = await manager_with_redis.remove_pending_job("ORD-600")
        assert result is True
        manager_with_redis._redis.lrem.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_pending_job_not_found(self, manager_with_redis):
        """Удаление несуществующего чека — False."""
        manager_with_redis._redis.lrange.return_value = []
        result = await manager_with_redis.remove_pending_job("ORD-NONEXISTENT")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_pending_without_redis(self, manager):
        """Без Redis remove_pending_job возвращает False."""
        result = await manager.remove_pending_job("ORD-700")
        assert result is False


# --- Тесты повторной печати ---

class TestRetryPrint:

    @pytest.mark.asyncio
    async def test_retry_no_printer(self, manager_with_redis):
        """Повторная печать без принтера — False."""
        order = make_order_data("ORD-700")
        manager_with_redis._redis.lrange.return_value = [json.dumps(order)]

        result = await manager_with_redis.retry_print_job("ORD-700")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_job_not_in_queue(self, manager_with_redis):
        """Повторная печать чека, которого нет в очереди — False."""
        ws = make_mock_ws()
        await manager_with_redis.connect(ws, "client-1")

        manager_with_redis._redis.lrange.return_value = []
        result = await manager_with_redis.retry_print_job("ORD-NONEXISTENT")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_success(self, manager_with_redis):
        """Успешная повторная печать — чек отправляется и удаляется из очереди."""
        ws = make_mock_ws()
        await manager_with_redis.connect(ws, "client-1")

        order = make_order_data("ORD-800")
        manager_with_redis._redis.lrange.return_value = [json.dumps(order)]

        result = await manager_with_redis.retry_print_job("ORD-800")

        assert result is True
        ws.send_json.assert_called_once_with(order)
