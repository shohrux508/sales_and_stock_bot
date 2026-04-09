import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
else:
    APP_PATH = os.path.dirname(os.path.abspath(__file__))

env_path = Path(APP_PATH) / ".env"
load_dotenv(dotenv_path=env_path)

# ============================================
# Настройки клиента печати чеков (Xprinter)
# ============================================

# URL WebSocket-сервера
# По умолчанию берется из переменной SERVER_WS_URL или хардкод
SERVER_WS_URL = os.getenv("SERVER_WS_URL", "wss://salesmanager.up.railway.app/ws/printer/{token}")

# Секретный токен (должен совпадать с PRINTER_SECRET_TOKEN в .env сервера)
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "xprinter-sale-stock-2026-secret")

# ID продавца
SELLER_ID = os.getenv("SELLER_ID", "")

# Интервал переподключения при обрыве связи (секунды)
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))

# ============================================
# Настройки USB-принтера Xprinter
# ============================================
# Стандартные значения для Xprinter XP-58IIH / XP-365B
PRINTER_VENDOR_ID = int(os.getenv("PRINTER_VENDOR_ID", "0x0483"), 16)
PRINTER_PRODUCT_ID = int(os.getenv("PRINTER_PRODUCT_ID", "0x070B"), 16)

# Альтернатива: имя принтера Windows
PRINTER_NAME_WIN = os.getenv("PRINTER_NAME_WIN", "POSPrinter POS58")

# ============================================
# Настройки чека
# ============================================
SHOP_NAME = os.getenv("SHOP_NAME", "Sale & Stock Bot")
RECEIPT_WIDTH = int(os.getenv("RECEIPT_WIDTH", "32"))

# Режим принтера: "usb" или "windows"
PRINTER_MODE = os.getenv("PRINTER_MODE", "windows")
