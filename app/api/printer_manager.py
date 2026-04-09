"""
Менеджер WebSocket-соединений для принтеров чеков.

Обеспечивает:
- Хранение активных WebSocket-сессий принтеров
- Дедупликацию order_id через Redis
- Отправку заданий на печать подключенным клиентам
- Очередь непечатанных чеков (для fallback через Telegram)
"""

import logging
import json
from typing import Optional
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class PrinterConnectionManager:
    """Singleton-менеджер для управления подключениями принтеров по WebSocket."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._redis = None
        self._redis_available = False
        self._pending_key = "printer:pending_jobs"
        self._max_pending = 100

    async def init_redis(self, redis_url: str) -> None:
        """Инициализация Redis-соединения для дедупликации."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._redis_available = True
            logger.info("PrinterManager: Redis подключен для дедупликации чеков")
        except Exception as e:
            logger.warning(f"PrinterManager: Redis недоступен ({e}), дедупликация отключена")
            self._redis_available = False

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Регистрирует новое WebSocket-соединение принтера."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"🖨️ Принтер подключен (ID: {client_id[:8]}...). "
                     f"Всего подключений: {len(self.active_connections)}")

    def disconnect(self, client_id: str) -> None:
        """Удаляет соединение из менеджера."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"🖨️ Принтер отключен (ID: {client_id[:8]}...). "
                         f"Всего подключений: {len(self.active_connections)}")

    @property
    def has_connected_printer(self) -> bool:
        """Есть ли хотя бы один подключенный принтер."""
        return len(self.active_connections) > 0

    async def get_all_pending_jobs(self) -> list[dict]:
        """Получает все чеки в очереди из Redis."""
        if not self._redis_available:
            return []
        try:
            jobs_raw = await self._redis.lrange(self._pending_key, 0, -1)
            return [json.loads(j) for j in jobs_raw]
        except Exception as e:
            logger.error(f"Redis error getting pending jobs: {e}")
            return []

    async def is_duplicate(self, order_id: str) -> bool:
        """Проверяет, был ли уже отправлен чек с таким order_id (через Redis)."""
        if not self._redis_available or not self._redis:
            return False
        try:
            exists = await self._redis.exists(f"printed_order:{order_id}")
            return bool(exists)
        except Exception as e:
            logger.error(f"Redis ошибка при проверке дубликата: {e}")
            return False

    async def _mark_as_printed(self, order_id: str) -> None:
        """Помечает order_id как напечатанный в Redis (TTL = 24 часа)."""
        if not self._redis_available or not self._redis:
            return
        try:
            await self._redis.set(f"printed_order:{order_id}", "1", ex=86400)
        except Exception as e:
            logger.error(f"Redis ошибка при сохранении order_id: {e}")

    async def send_print_job(self, order_data: dict) -> bool:
        """
        Отправляет задание на печать подключенному принтеру.
        
        Returns:
            True — если чек отправлен успешно
            False — если нет подключенных принтеров или дубль
        """
        order_id = order_data.get("order_id", "")
        seller_id = order_data.get("seller_id", None)

        # Проверка на дубликат
        if await self.is_duplicate(order_id):
            logger.warning(f"Дубликат чека {order_id} — пропущен")
            return False

        # Попытка отправить на конкретный принтер (по seller_id)
        if seller_id and str(seller_id) in self.active_connections:
            ws = self.active_connections[str(seller_id)]
            try:
                await ws.send_json(order_data)
                await self._mark_as_printed(order_id)
                logger.info(f"✅ Чек {order_id} отправлен на принтер продавца {seller_id}")
                return True
            except Exception as e:
                logger.error(f"Ошибка отправки на принтер продавца {seller_id}: {e}")
                self.disconnect(str(seller_id))
        elif seller_id:
            logger.warning(f"Принтер продавца {seller_id} не подключен. Чек {order_id} добавлен в очередь.")
        else:
            # Fallback (для старых клиентов без seller_id)
            disconnected = []
            for client_id, ws in self.active_connections.items():
                try:
                    await ws.send_json(order_data)
                    await self._mark_as_printed(order_id)
                    logger.info(f"✅ Чек {order_id} отправлен на общий принтер {client_id[:8]}...")
                    return True
                except Exception as e:
                    logger.error(f"Ошибка отправки на общий принтер {client_id[:8]}...: {e}")
                    disconnected.append(client_id)

            # Очистка отключенных
            for client_id in disconnected:
                self.disconnect(client_id)
            
            logger.warning(f"Нет общих подключенных принтеров. Чек {order_id} добавлен в очередь.")

        # Добавляем в очередь, если не удалось напечатать
        await self._add_to_pending(order_data)
        return False

    async def _add_to_pending(self, order_data: dict) -> None:
        """Добавляет чек в очередь непечатанных в Redis."""
        if not self._redis_available:
            return
        try:
            # Add to list and trim to max size
            await self._redis.rpush(self._pending_key, json.dumps(order_data))
            await self._redis.ltrim(self._pending_key, -self._max_pending, -1)
            # Set TTL for the whole queue just in case
            await self._redis.expire(self._pending_key, 604800) # 1 week
        except Exception as e:
            logger.error(f"Redis error adding to pending: {e}")

    async def get_pending_job(self, order_id: str) -> Optional[dict]:
        """Получает конкретный чек из очереди по order_id."""
        jobs = await self.get_all_pending_jobs()
        for job in jobs:
            if job.get("order_id") == order_id:
                return job
        return None

    async def remove_pending_job(self, order_id: str) -> bool:
        """Удаляет чек из очереди в Redis."""
        if not self._redis_available:
            return False
        try:
            jobs = await self.get_all_pending_jobs()
            for job in jobs:
                if job.get("order_id") == order_id:
                    await self._redis.lrem(self._pending_key, 1, json.dumps(job))
                    return True
        except Exception as e:
            logger.error(f"Redis error removing job: {e}")
        return False

    async def retry_print_job(self, order_id: str) -> bool:
        """
        Повторная попытка печати чека из очереди (вызов по кнопке из Telegram).
        """
        job = await self.get_pending_job(order_id)
        if not job:
            logger.warning(f"Чек {order_id} не найден в очереди")
            return False

        if not self.has_connected_printer:
            logger.warning(f"Принтер не подключен для повторной печати {order_id}")
            return False

        # Пытаемся отправить
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_json(job)
                await self._mark_as_printed(order_id)
                await self.remove_pending_job(order_id)
                logger.info(f"✅ Повторная печать чека {order_id} — успешно")
                return True
            except Exception as e:
                logger.error(f"Ошибка повторной печати: {e}")

        return False
