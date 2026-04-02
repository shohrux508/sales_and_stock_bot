"""
WebSocket-клиент для получения заданий на печать чеков.

Особенности:
- Автоматическое подключение и переподключение при обрыве
- Обработка JSON → ESC/POS через receipt_printer
- Устойчивость к ошибкам принтера (USBError, OSError)
- Логирование всех событий в консоль
"""

import asyncio
import json
import logging
import sys
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from config import SERVER_WS_URL, SECRET_TOKEN, RECONNECT_DELAY, PRINTER_MODE
from receipt_printer import print_receipt, print_receipt_console

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("printer_client")

# Определяем, доступен ли реальный принтер
REAL_PRINTER_AVAILABLE = False

def check_printer():
    """Проверка доступности принтера."""
    global REAL_PRINTER_AVAILABLE
    
    if PRINTER_MODE == "usb":
        try:
            from escpos.printer import Usb
            from config import PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID
            p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID)
            p.close()
            REAL_PRINTER_AVAILABLE = True
            logger.info("✅ USB-принтер обнаружен и доступен")
        except Exception as e:
            REAL_PRINTER_AVAILABLE = False
            logger.warning(f"⚠️ USB-принтер недоступен: {e}")
            logger.info("📋 Работаю в режиме консольной печати (тестовый)")
    elif PRINTER_MODE == "windows":
        try:
            import win32print
            from config import PRINTER_NAME_WIN
            printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
            if PRINTER_NAME_WIN in printers:
                REAL_PRINTER_AVAILABLE = True
                logger.info(f"✅ Windows-принтер '{PRINTER_NAME_WIN}' обнаружен")
            else:
                REAL_PRINTER_AVAILABLE = False
                logger.warning(f"⚠️ Принтер '{PRINTER_NAME_WIN}' не найден. Доступны: {printers}")
        except Exception as e:
            REAL_PRINTER_AVAILABLE = False
            logger.warning(f"⚠️ Windows-принтер недоступен: {e}")
    else:
        REAL_PRINTER_AVAILABLE = False
        logger.info("📋 Режим — только консольная печать")


def handle_print_job(data: dict) -> None:
    """Обработка задания на печать."""
    order_id = data.get("order_id", "N/A")
    
    # Тестовая печать в консоль всегда
    print_receipt_console(data)
    
    # Попытка реальной печати
    if REAL_PRINTER_AVAILABLE:
        try:
            print_receipt(data)
            logger.info(f"🖨️ Чек #{order_id} напечатан на принтере")
        except Exception as e:
            logger.error(f"❌ Ошибка принтера при печати чека #{order_id}: {e}")
            logger.info("Принтер выключен или закончилась бумага. Ожидание исправления...")
            raise  # Пробрасываем для отправки ERROR на сервер
    else:
        logger.info(f"📋 Чек #{order_id} выведен только в консоль (принтер не подключен)")


async def run_client():
    """Основной цикл WebSocket-клиента."""
    url = SERVER_WS_URL.format(token=SECRET_TOKEN)
    
    logger.info("=" * 50)
    logger.info("  Sale & Stock Bot — Printer Client")
    logger.info("=" * 50)
    logger.info(f"Сервер: {url[:url.index(SECRET_TOKEN[:8])]}" + "***")
    
    # Проверяем принтер при старте
    check_printer()
    
    while True:
        try:
            logger.info("🔗 Подключение к серверу...")
            
            async with websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                logger.info("✅ Подключено к серверу! Ожидание заданий на печать...")
                
                while True:
                    try:
                        message = await ws.recv()
                        
                        # Обработка pong от сервера
                        if message == "pong":
                            continue
                        
                        # Парсинг JSON
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            logger.warning(f"Получены некорректные данные: {message[:100]}")
                            continue
                        
                        order_id = data.get("order_id", "N/A")
                        logger.info(f"📩 Получено задание на печать чека #{order_id}")
                        
                        # Печать
                        try:
                            handle_print_job(data)
                            await ws.send("ACK")
                            logger.info(f"✅ ACK отправлен для чека #{order_id}")
                        except Exception as e:
                            error_msg = str(e)
                            await ws.send(f"ERROR:{error_msg}")
                            logger.error(f"❌ ERROR отправлен для чека #{order_id}: {error_msg}")
                            
                    except ConnectionClosedOK:
                        logger.info("Соединение закрыто сервером (нормально)")
                        break
                    except ConnectionClosedError as e:
                        logger.warning(f"Соединение закрыто с ошибкой: {e}")
                        break
                        
        except ConnectionRefusedError:
            logger.error(f"❌ Сервер недоступен. Повторная попытка через {RECONNECT_DELAY}с...")
        except OSError as e:
            logger.error(f"❌ Сетевая ошибка: {e}. Повторная попытка через {RECONNECT_DELAY}с...")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}. Повторная попытка через {RECONNECT_DELAY}с...")
        
        # Переподключение
        await asyncio.sleep(RECONNECT_DELAY)
        
        # Перепроверяем принтер при каждом переподключении
        check_printer()


def main():
    """Точка входа."""
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        logger.info("\n👋 Клиент остановлен пользователем (Ctrl+C)")
        sys.exit(0)


if __name__ == "__main__":
    main()
