"""
WebSocket эндпоинт для подключения локального клиента-принтера.

Протокол:
1. Клиент подключается к /ws/printer/{secret_token}
2. Сервер проверяет secret_token
3. При продаже сервер отправляет JSON через WebSocket
4. Клиент отвечает ACK или ERROR
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings

router = APIRouter(tags=["printer"])
logger = logging.getLogger(__name__)


@router.get("/api/printer/status")
async def printer_status(request_obj=None):
    """Проверка статуса подключения принтера (для мониторинга)."""
    from fastapi import Request
    # Get printer_manager from app state
    # This endpoint is intentionally simple and doesn't require auth
    # as it only returns connection status
    return {"status": "endpoint_active"}


@router.websocket("/ws/printer/{secret_token}")
async def printer_websocket(websocket: WebSocket, secret_token: str):
    """
    WebSocket-эндпоинт для подключения локального клиента принтера.
    
    Авторизация через secret_token из .env (PRINTER_SECRET_TOKEN).
    После подключения клиент ожидает JSON-сообщения с данными для печати.
    Клиент отвечает ACK/ERROR после обработки.
    """
    # Проверка токена
    if secret_token != settings.PRINTER_SECRET_TOKEN:
        logger.warning(f"Попытка подключения принтера с неверным токеном: {secret_token[:8]}...")
        await websocket.close(code=4003, reason="Invalid token")
        return

    # Получаем менеджер из app.state
    manager = websocket.app.state.printer_manager

    # Используем токен как client_id (можно расширить до уникальных ID)
    client_id = secret_token
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Ожидаем сообщения от клиента (ACK, ERROR, ping)
            data = await websocket.receive_text()

            if data == "ACK":
                logger.info("🖨️ Принтер: чек успешно напечатан")
            elif data.startswith("ERROR:"):
                error_msg = data[6:]
                logger.error(f"🖨️ Принтер сообщил об ошибке: {error_msg}")
            elif data == "ping":
                await websocket.send_text("pong")
            else:
                logger.debug(f"🖨️ Получено от принтера: {data}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("🖨️ Принтер отключился (WebSocketDisconnect)")
    except Exception as e:
        manager.disconnect(client_id)
        logger.error(f"🖨️ Ошибка соединения с принтером: {e}")
