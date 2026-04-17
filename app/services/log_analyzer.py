"""
Log Analyzer (Дежурный) — сервис ежедневного анализа логов.

Читает logs/sales_bot.log с конца файла, ищет ключевые паттерны
за текущие сутки (UZT +5), агрегирует статистику и отправляет
сводный отчёт TECH_ADMIN_ID через Telegram.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Таймзона Узбекистана (UTC+5)
UZT = timezone(timedelta(hours=5))

# Формат даты в логах loguru
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Размер чанка для reverse-read (8 KB)
CHUNK_SIZE = 8192


@dataclass
class LogStats:
    """Агрегированная статистика за день."""

    # Принтер
    prints_success: int = 0
    prints_retry_success: int = 0
    printer_no_connection: int = 0
    printer_seller_offline: int = 0
    printer_errors: int = 0
    receipt_duplicates: int = 0
    printer_connects: int = 0
    printer_disconnects: int = 0

    # Система
    bot_restarts: int = 0
    telegram_errors: int = 0
    redis_errors: int = 0

    # Общее
    total_lines: int = 0
    total_warnings: int = 0
    total_errors: int = 0

    # Детали ошибок (последние 5)
    error_samples: list = field(default_factory=list)


# Паттерны для классификации: (compiled_regex, attribute_name_to_increment)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Принтер — успех
    (re.compile(r"Чек .+ отправлен на принтер"), "prints_success"),
    (re.compile(r"Повторная печать чека .+ — успешно"), "prints_retry_success"),
    # Принтер — предупреждения
    (re.compile(r"Нет подключенных принтеров|Нет общих подключенных принтеров"), "printer_no_connection"),
    (re.compile(r"Принтер продавца .+ не подключен"), "printer_seller_offline"),
    (re.compile(r"Дубликат чека"), "receipt_duplicates"),
    # Принтер — ошибки
    (re.compile(r"Ошибка отправки на принтер|Ошибка повторной печати|Принтер сообщил об ошибке"), "printer_errors"),
    # Принтер — подключения
    (re.compile(r"Принтер подключен"), "printer_connects"),
    (re.compile(r"Принтер отключен|Принтер отключился"), "printer_disconnects"),
    # Система
    (re.compile(r"Setting up services"), "bot_restarts"),
    (re.compile(r"Failed to fetch updates|TelegramNetworkError|TelegramServerError"), "telegram_errors"),
    (re.compile(r"Redis error|Redis ошибка"), "redis_errors"),
]


class LogAnalyzerService:
    """Сервис анализа лог-файла с ежедневным отчётом."""

    def __init__(self, log_path: str = "logs/sales_bot.log"):
        self.log_path = Path(log_path)
        self._report_sent_date: datetime | None = None

    # ── Публичные методы ──────────────────────────────────────────

    def analyze_today(self) -> LogStats:
        """Анализирует лог-файл за текущие сутки (UZT +5)."""
        return self.analyze(days=1)

    def analyze(self, days: int = 1) -> LogStats:
        """
        Анализирует лог-файл за указанное количество дней (UZT +5).

        Ограничено 10 днями для производительности.
        """
        # Ограничиваем период до 10 дней
        days = max(1, min(days, 10))

        stats = LogStats()

        if not self.log_path.exists():
            logger.warning(f"Лог-файл не найден: {self.log_path}")
            return stats

        start_time = self._get_start_time(days)

        for line in self._read_lines_reverse(self.log_path):
            line = line.strip()
            if not line:
                continue

            parsed = self._parse_log_line(line)
            if parsed is None:
                # Строка без даты (часть traceback) — пропускаем
                continue

            log_dt, level, message = parsed

            # Остановка: вышли за пределы периода
            if log_dt < start_time:
                break

            stats.total_lines += 1

            # Подсчёт по уровням
            if level == "ERROR":
                stats.total_errors += 1
                if len(stats.error_samples) < 5:
                    # Укорачиваем сообщение для отчёта
                    stats.error_samples.append(message[:120])
            elif level == "WARNING":
                stats.total_warnings += 1

            # Классификация по паттернам
            self._classify_event(message, stats)

        return stats

    def format_report(self, stats: LogStats, days: int = 1, report_date: datetime | None = None) -> str:
        """Форматирует статистику в Telegram-сообщение."""
        if report_date is None:
            report_date = datetime.now(UZT)

        days = max(1, min(days, 10))

        if days == 1:
            date_info = report_date.strftime("%d.%m.%Y")
        else:
            start_date = (report_date - timedelta(days=days - 1)).strftime("%d.%m")
            end_date = report_date.strftime("%d.%m.%Y")
            date_info = f"{start_date} - {end_date}"

        time_str = report_date.strftime("%H:%M")

        lines = [
            f"📊 <b>Дежурный отчёт за {date_info}</b>",
            "",
            "🖨️ <b>Принтер</b>",
            f"  ✅ Чеки напечатаны: <b>{stats.prints_success}</b>",
        ]

        if stats.prints_retry_success:
            lines.append(f"  🔁 Повторная печать: <b>{stats.prints_retry_success}</b>")

        lines.extend(
            [
                f"  ⚠️ Нет принтеров: <b>{stats.printer_no_connection}</b>",
            ]
        )

        if stats.printer_seller_offline:
            lines.append(f"  ⚠️ Принтер продавца офлайн: <b>{stats.printer_seller_offline}</b>")

        lines.extend(
            [
                f"  ❌ Ошибки печати: <b>{stats.printer_errors}</b>",
                f"  🔁 Дубликаты: <b>{stats.receipt_duplicates}</b>",
                f"  🔌 Подключений: <b>{stats.printer_connects}</b> | Отключений: <b>{stats.printer_disconnects}</b>",
                "",
                "🤖 <b>Система</b>",
                f"  🔄 Перезапусков бота: <b>{stats.bot_restarts}</b>",
                f"  ❌ Telegram ошибки: <b>{stats.telegram_errors}</b>",
                f"  ❌ Redis ошибки: <b>{stats.redis_errors}</b>",
                "",
                "📈 <b>Общее</b>",
                f"  ℹ️ Строк за период: <b>{stats.total_lines}</b>",
                f"  ⚠️ Warnings: <b>{stats.total_warnings}</b>",
                f"  ❌ Errors: <b>{stats.total_errors}</b>",
            ]
        )

        # Последние ошибки
        if stats.error_samples:
            lines.append("")
            lines.append("🔍 <b>Последние ошибки:</b>")
            for i, sample in enumerate(stats.error_samples, 1):
                lines.append(f"  {i}. <code>{sample}</code>")

        lines.extend(
            [
                "",
                f"⏰ Отчёт сформирован: {time_str}",
            ]
        )

        return "\n".join(lines)

    async def send_report(self, bot, chat_id: int, days: int = 1) -> bool:
        """Анализирует логи и отправляет отчёт в Telegram."""
        try:
            stats = self.analyze(days=days)
            report = self.format_report(stats, days=days)
            await bot.send_message(
                chat_id=chat_id,
                text=report,
                parse_mode="HTML",
            )
            logger.info(f"📊 Дежурный отчёт отправлен (days={days}, chat_id={chat_id})")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки дежурного отчёта: {e}")
            return False

    async def scheduler_loop(self, bot, chat_id: int, report_time: str = "23:55"):
        """
        Фоновый цикл-планировщик для ежедневной отправки отчёта.

        Args:
            bot: aiogram Bot instance
            chat_id: Telegram ID получателя (TECH_ADMIN_ID)
            report_time: Время отправки в формате HH:MM (UZT +5)
        """
        target_hour, target_minute = map(int, report_time.split(":"))
        logger.info(f"📊 Log Analyzer запущен. Отчёт будет отправляться в {report_time} (UZT)")

        while True:
            try:
                now = datetime.now(UZT)
                today = now.date()

                # Проверяем, нужно ли отправить отчёт
                if now.hour == target_hour and now.minute == target_minute and self._report_sent_date != today:
                    await self.send_report(bot, chat_id)
                    self._report_sent_date = today

                # Спим 30 секунд — достаточная точность для ежедневного отчёта
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("📊 Log Analyzer scheduler остановлен")
                break
            except Exception as e:
                logger.error(f"📊 Log Analyzer scheduler ошибка: {e}")
                await asyncio.sleep(60)

    # ── Приватные методы ──────────────────────────────────────────

    @staticmethod
    def _get_start_time(days: int) -> datetime:
        """Возвращает начало периода в UZT (+5) как aware datetime."""
        now = datetime.now(UZT)
        # Начало суток 'days-1' назад
        return (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _parse_log_line(line: str) -> tuple[datetime, str, str] | None:
        """
        Парсит строку лога.

        Формат: "2026-03-27 18:32:12 | INFO     | name:func:line - message"

        Возвращает (datetime, level, message) или None если строка не парсится.
        """
        # Быстрая проверка: строка лога начинается с даты "YYYY-"
        if len(line) < 25 or not line[0:5].replace("-", "").isdigit():
            return None

        try:
            # Дата: первые 19 символов
            date_str = line[:19]
            log_dt = datetime.strptime(date_str, LOG_DATE_FORMAT).replace(tzinfo=UZT)

            # Уровень: после " | " — обрезаем пробелы
            rest = line[22:]  # после "2026-03-27 18:32:12 | "
            pipe_idx = rest.find("|")
            if pipe_idx == -1:
                return None

            level = rest[:pipe_idx].strip()

            # Сообщение: после " - " в остатке
            dash_idx = rest.find(" - ", pipe_idx)
            if dash_idx == -1:
                message = rest[pipe_idx + 1 :].strip()
            else:
                message = rest[dash_idx + 3 :].strip()

            return log_dt, level, message

        except (ValueError, IndexError):
            return None

    @staticmethod
    def _classify_event(message: str, stats: LogStats) -> None:
        """Сопоставляет сообщение с паттернами и обновляет счётчик."""
        for pattern, attr_name in _PATTERNS:
            if pattern.search(message):
                setattr(stats, attr_name, getattr(stats, attr_name) + 1)
                return  # Одна строка = один паттерн (первый совпавший)

    @staticmethod
    def _read_lines_reverse(filepath: Path):
        """
        Генератор: читает файл с конца, возвращая строки в обратном порядке.

        Эффективно работает с большими файлами — читает чанками по CHUNK_SIZE.
        """
        with open(filepath, "rb") as f:
            # Перемещаемся в конец файла
            f.seek(0, os.SEEK_END)
            file_size = f.tell()

            if file_size == 0:
                return

            remaining = b""
            offset = file_size

            while offset > 0:
                # Размер чанка для чтения
                chunk_size = min(CHUNK_SIZE, offset)
                offset -= chunk_size

                f.seek(offset)
                chunk = f.read(chunk_size)

                # Объединяем с остатком от предыдущего чтения
                chunk = chunk + remaining

                # Разбиваем на строки
                lines = chunk.split(b"\n")

                # Первая «строка» может быть неполной — сохраняем как остаток
                remaining = lines[0]

                # Возвращаем строки с конца (кроме первой неполной)
                for line in reversed(lines[1:]):
                    decoded = line.decode("utf-8", errors="replace").rstrip("\r")
                    if decoded:
                        yield decoded

            # Возвращаем оставшуюся первую строку файла
            if remaining:
                decoded = remaining.decode("utf-8", errors="replace").rstrip("\r")
                if decoded:
                    yield decoded
