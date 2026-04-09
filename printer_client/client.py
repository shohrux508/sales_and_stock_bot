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
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path
from dotenv import set_key

from config import SERVER_WS_URL, SECRET_TOKEN, RECONNECT_DELAY, PRINTER_MODE, SHOP_NAME, SELLER_ID
from receipt_printer import print_receipt, print_receipt_console

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("printer_client")

# Глобальные переменные для управления состоянием
REAL_PRINTER_AVAILABLE = False
tray_icon = None

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
    total_amount = data.get("total_amount", 0)
    currency = data.get("currency", "UZS")
    
    # Показываем уведомление в Windows
    if tray_icon:
        tray_icon.notify(f"Сумма: {total_amount:,.0f} {currency}", "🖨️ Получен новый чек!")
    
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


async def run_client(current_seller_id: str):
    """Основной цикл WebSocket-клиента."""
    url = SERVER_WS_URL.format(token=SECRET_TOKEN)
    if current_seller_id:
        url += f"?seller_id={current_seller_id}"
    
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
                
                # Обновляем статус в трее
                if tray_icon:
                    tray_icon.title = f"{SHOP_NAME}: Подключен"
                
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
        
        # Обновляем статус при ошибке подключения
        if tray_icon:
            tray_icon.title = f"{SHOP_NAME}: Отключен (переподключение...)"
        
        # Переподключение
        await asyncio.sleep(RECONNECT_DELAY)
        
        # Перепроверяем принтер при каждом переподключении
        check_printer()


def create_image():
    """Создает простую иконку принтера для трея."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    
    # Рисуем упрощенную иконку принтера (синий прямоугольник с белым листом)
    dc.rectangle([10, 20, 54, 50], fill=(50, 50, 200)) # Корпус
    dc.rectangle([15, 10, 49, 25], fill=(220, 220, 220)) # Бумага сверху
    dc.rectangle([15, 45, 49, 60], fill=(220, 220, 220)) # Чек снизу
    
    return image

def show_settings_gui():
    """Показывает GUI для настройки."""
    global SELLER_ID
    import config
    
    root = tk.Tk()
    root.withdraw() # Скрываем главное окно
    
    # Запрос ID продавца
    new_seller_id = simpledialog.askstring(
        "Настройка клиента принтера", 
        "Введите ваш ID продавца (можно узнать в боте по команде /start):", 
        initialvalue=config.SELLER_ID
    )
    if not new_seller_id:
        return
        
    # Запрос имени принтера
    new_printer_name = simpledialog.askstring(
        "Настройка клиента принтера", 
        "Введите имя принтера Windows:\n(оставьте как есть, если не знаете)", 
        initialvalue=config.PRINTER_NAME_WIN
    )
    if not new_printer_name:
        return
        
    # Сохраняем в .env
    env_path = Path(".") / ".env"
    env_path.touch(exist_ok=True)
    
    set_key(env_path, "SELLER_ID", new_seller_id)
    set_key(env_path, "PRINTER_NAME_WIN", new_printer_name)
    
    # Обновляем переменные в памяти для текущего запуска
    config.SELLER_ID = new_seller_id
    config.PRINTER_NAME_WIN = new_printer_name
    
    messagebox.showinfo("Настройки сохранены", "Настройки обновлены! Пожалуйста, перезапустите приложение.")
    
    # Если изменяем настройки "на лету", лучше выйти для чистого рестарта
    os._exit(0)

def on_quit(icon, item):
    """Выход из приложения."""
    logger.info("Завершение работы через трей...")
    icon.stop()
    os._exit(0)

def on_change_settings(icon, item):
    """Изменение настроек через трей."""
    # Запускаем в отдельном потоке чтобы не блокировать трей
    threading.Thread(target=show_settings_gui, daemon=True).start()

def setup_tray():
    """Настройка и запуск иконки в трее."""
    global tray_icon
    icon_image = create_image()
    menu = (
        item('Настройки', on_change_settings),
        item('Выход', on_quit),
    )
    tray_icon = pystray.Icon("printer_client", icon_image, f"{SHOP_NAME}: Инициализация...", menu)
    
    # Показываем уведомление при запуске
    tray_icon.run(setup=lambda icon: icon.notify("Приложение запущено и работает в фоне", SHOP_NAME))

def main():
    """Точка входа."""
    import config
    
    # Проверка настроек при старте
    if not config.SELLER_ID:
        # Если ID продавца нет, показываем диалог настройки
        show_settings_gui()
        # Если после диалога ID всё ещё нет (отменили), выходим
        if not config.SELLER_ID:
            sys.exit(0)

    try:
        # Запускаем WebSocket клиент в отдельном потоке
        # Передаем обновленный seller_id
        client_thread = threading.Thread(target=lambda: asyncio.run(run_client(config.SELLER_ID)), daemon=True)
        client_thread.start()
        
        # Запускаем иконку в трее (основной поток)
        setup_tray()
    except KeyboardInterrupt:
        logger.info("\n👋 Клиент остановлен пользователем (Ctrl+C)")
        sys.exit(0)

if __name__ == "__main__":
    import os
    main()
