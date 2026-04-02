"""
Модуль формирования и печати чеков на термопринтере Xprinter.

Поддержка:
- USB режим (python-escpos + pyusb + Zadig)
- Windows режим (win32print)
- Кириллица и латиница (CP866 / UTF-8)
- Настраиваемая ширина бумаги (58mm / 80mm)
"""

import logging
from config import (
    PRINTER_VENDOR_ID,
    PRINTER_PRODUCT_ID,
    PRINTER_NAME_WIN,
    SHOP_NAME,
    RECEIPT_WIDTH,
    PRINTER_MODE,
)

logger = logging.getLogger(__name__)


def format_receipt_text(data: dict) -> str:
    """
    Форматирует данные чека в текстовый вид (для отладки без принтера).
    """
    w = RECEIPT_WIDTH
    lines = []
    lines.append("=" * w)
    lines.append(SHOP_NAME.center(w))
    lines.append("=" * w)
    lines.append(f"Chek: {data.get('order_id', 'N/A')}")
    lines.append(f"Xodim: {data.get('worker_name', 'N/A')}")
    lines.append(f"Sana: {data.get('timestamp', 'N/A')}")
    lines.append("-" * w)

    # Шапка таблицы
    lines.append(f"{'Nomi':<{w-14}}{'Son':>4}{'Summa':>10}")
    lines.append("-" * w)

    # Товары
    for item in data.get("items", []):
        name = item.get("name", "???")
        qty = item.get("quantity", 0)
        total = item.get("sum", 0)

        # Если имя длиннее — обрезаем
        max_name_len = w - 14
        if len(name) > max_name_len:
            name = name[: max_name_len - 1] + "."

        lines.append(f"{name:<{max_name_len}}{qty:>4}{total:>10,}")

    lines.append("-" * w)

    # Итого
    currency = data.get("currency", "UZS")
    total_amount = data.get("total_amount", 0)
    total_line = f"JAMI: {total_amount:,} {currency}"
    lines.append(total_line.rjust(w))

    lines.append("")
    lines.append(data.get("timestamp", "").center(w))
    lines.append("")
    lines.append("Rahmat! Xaridingiz uchun".center(w))
    lines.append("minnatdormiz!".center(w))
    lines.append("")
    lines.append("=" * w)

    return "\n".join(lines)


def print_receipt_usb(data: dict) -> None:
    """Печать чека через USB (python-escpos)."""
    try:
        from escpos.printer import Usb
    except ImportError:
        raise ImportError(
            "python-escpos не установлен. Установите: pip install python-escpos"
        )

    p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID)

    try:
        # Header
        p.set(align="center", bold=True, double_height=True, double_width=True)
        p.text(f"{SHOP_NAME}\n")
        p.set(align="center", bold=False, double_height=False, double_width=False)
        p.text(f"Chek: {data.get('order_id', 'N/A')}\n")
        p.text(f"Xodim: {data.get('worker_name', 'N/A')}\n")
        p.text(f"Sana: {data.get('timestamp', 'N/A')}\n")
        p.text("=" * RECEIPT_WIDTH + "\n")

        # Body — товары
        p.set(align="left", bold=False)
        for item in data.get("items", []):
            name = item.get("name", "???")
            qty = item.get("quantity", 0)
            price = item.get("price", 0)
            total = item.get("sum", 0)

            max_name = RECEIPT_WIDTH - 4
            if len(name) > max_name:
                name = name[: max_name - 1] + "."

            p.text(f"{name}\n")
            p.text(f"  {price:,} x {qty} = {total:,}\n")

        p.text("-" * RECEIPT_WIDTH + "\n")

        # Footer — итого
        currency = data.get("currency", "UZS")
        total_amount = data.get("total_amount", 0)

        p.set(align="right", bold=True, double_height=True)
        p.text(f"JAMI: {total_amount:,} {currency}\n")

        p.set(align="center", bold=False, double_height=False)
        p.text(f"\n{data.get('timestamp', '')}\n\n")
        p.text("Rahmat! Xaridingiz uchun\n")
        p.text("minnatdormiz!\n\n")

        # Cut
        p.cut()
    finally:
        try:
            p.close()
        except Exception:
            pass


def print_receipt_windows(data: dict) -> None:
    """Печать чека через стандартный Windows-драйвер (fallback)."""
    try:
        import win32print
        import win32ui
    except ImportError:
        raise ImportError(
            "pywin32 не установлен. Установите: pip install pywin32"
        )

    text = format_receipt_text(data)

    # Используем RAW печать
    printer_handle = win32print.OpenPrinter(PRINTER_NAME_WIN)
    try:
        job = win32print.StartDocPrinter(printer_handle, 1, ("Receipt", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        win32print.WritePrinter(printer_handle, text.encode("cp866", errors="replace"))
        # Добавляем команду обрезки (ESC/POS)
        win32print.WritePrinter(printer_handle, b"\x1d\x56\x00")  # Full cut
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
    finally:
        win32print.ClosePrinter(printer_handle)


def print_receipt(data: dict) -> None:
    """
    Главная функция печати чека.
    Выбирает режим в зависимости от конфигурации (USB / Windows).
    """
    logger.info(f"Печать чека #{data.get('order_id', '???')} в режиме '{PRINTER_MODE}'")

    if PRINTER_MODE == "usb":
        print_receipt_usb(data)
    elif PRINTER_MODE == "windows":
        print_receipt_windows(data)
    else:
        raise ValueError(f"Неизвестный режим принтера: {PRINTER_MODE}")

    logger.info(f"Чек #{data.get('order_id', '???')} успешно напечатан")


def print_receipt_console(data: dict) -> None:
    """Тестовая печать — вывод в консоль (без принтера)."""
    text = format_receipt_text(data)
    print("\n" + text + "\n")
