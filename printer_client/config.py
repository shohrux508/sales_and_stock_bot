# ============================================
# Настройки клиента печати чеков (Xprinter)
# ============================================

# URL WebSocket-сервера (заменить на ваш домен)
# Для Railway/облака: wss://your-domain.com/ws/printer/{token}
# Для тестирования локально: ws://localhost:8000/ws/printer/{token}
SERVER_WS_URL = "wss://shohruxyigitaliev.uz/ws/printer/{token}"

# Секретный токен (должен совпадать с PRINTER_SECRET_TOKEN в .env сервера)
SECRET_TOKEN = "change-me-to-secure-token"

# Интервал переподключения при обрыве связи (секунды)
RECONNECT_DELAY = 5

# ============================================
# Настройки USB-принтера Xprinter
# ============================================
# Определить через Device Manager или Zadig (Windows)
# Стандартные значения для Xprinter XP-58IIH / XP-365B:
PRINTER_VENDOR_ID = 0x0416
PRINTER_PRODUCT_ID = 0x5011

# Альтернатива: использовать имя принтера Windows (fallback)
# Если USB не работает, можно использовать имя принтера из "Устройства и принтеры"
PRINTER_NAME_WIN = "XPrinter"

# ============================================
# Настройки чека
# ============================================
# Название магазина (шапка чека)
SHOP_NAME = "Sale & Stock Bot"

# Ширина бумаги (32 символа для 58mm, 48 символов для 80mm)
RECEIPT_WIDTH = 32

# Режим принтера: "usb" или "windows"
# "usb" — python-escpos через pyusb (требует Zadig)
# "windows" — через win32print (стандартный драйвер Windows)
PRINTER_MODE = "usb"
