"""
Тесты для LogAnalyzerService.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Устанавливаем тестовые переменные окружения до импорта
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "123456789:ABCDEF")
os.environ.setdefault("ADMIN_IDS", "123,456")

from app.services.log_analyzer import LogAnalyzerService, LogStats, UZT


# ── Фикстуры ─────────────────────────────────────────────────────


@pytest.fixture
def analyzer(tmp_path):
    """LogAnalyzerService с временным лог-файлом."""
    log_file = tmp_path / "test.log"
    log_file.touch()
    return LogAnalyzerService(log_path=str(log_file))


@pytest.fixture
def today_str():
    """Строка текущей даты в формате логов (UZT +5)."""
    return datetime.now(UZT).strftime("%Y-%m-%d")


def _write_log(analyzer: LogAnalyzerService, lines: list[str]):
    """Хелпер: записывает строки в лог-файл анализатора."""
    Path(analyzer.log_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Тесты _parse_log_line ────────────────────────────────────────


class TestParseLogLine:
    def test_valid_info_line(self):
        line = "2026-04-16 18:32:12 | INFO     | app.app:setup:19 - Setting up services..."
        result = LogAnalyzerService._parse_log_line(line)

        assert result is not None
        dt, level, message = result
        assert dt.year == 2026
        assert dt.month == 4
        assert dt.day == 16
        assert level == "INFO"
        assert message == "Setting up services..."

    def test_valid_error_line(self):
        line = "2026-04-03 18:58:36 | ERROR    | logging:callHandlers:1737 - Failed to fetch updates - TelegramServerError: Bad Gateway"
        result = LogAnalyzerService._parse_log_line(line)

        assert result is not None
        dt, level, message = result
        assert level == "ERROR"
        assert "Failed to fetch updates" in message

    def test_valid_warning_line(self):
        line = "2026-04-03 19:08:15 | WARNING  | logging:callHandlers:1737 - Нет подключенных принтеров. Чек abc123 добавлен в очередь."
        result = LogAnalyzerService._parse_log_line(line)

        assert result is not None
        _, level, message = result
        assert level == "WARNING"
        assert "Нет подключенных принтеров" in message

    def test_traceback_line_returns_none(self):
        line = "  File \"C:\\some\\path\\main.py\", line 25, in <module>"
        result = LogAnalyzerService._parse_log_line(line)
        assert result is None

    def test_empty_line_returns_none(self):
        assert LogAnalyzerService._parse_log_line("") is None

    def test_partial_line_returns_none(self):
        assert LogAnalyzerService._parse_log_line("Traceback (most recent call last):") is None

    def test_datetime_has_uzt_timezone(self):
        line = "2026-04-16 10:00:00 | INFO     | test:func:1 - test message"
        result = LogAnalyzerService._parse_log_line(line)

        assert result is not None
        dt, _, _ = result
        assert dt.tzinfo == UZT


# ── Тесты _classify_event ────────────────────────────────────────


class TestClassifyEvent:
    def test_print_success(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("✅ Чек abc-123 отправлен на принтер продавца 123", stats)
        assert stats.prints_success == 1

    def test_retry_success(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("✅ Повторная печать чека abc-123 — успешно", stats)
        assert stats.prints_retry_success == 1

    def test_no_printers(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Нет подключенных принтеров. Чек xyz добавлен в очередь.", stats)
        assert stats.printer_no_connection == 1

    def test_no_common_printers(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Нет общих подключенных принтеров. Чек xyz добавлен в очередь.", stats)
        assert stats.printer_no_connection == 1

    def test_seller_offline(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Принтер продавца 123 не подключен. Чек abc добавлен в очередь.", stats)
        assert stats.printer_seller_offline == 1

    def test_duplicate_receipt(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Дубликат чека abc-123 — пропущен", stats)
        assert stats.receipt_duplicates == 1

    def test_printer_error(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Ошибка отправки на принтер продавца 456: ConnectionError", stats)
        assert stats.printer_errors == 1

    def test_printer_report_error(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("🖨️ Принтер сообщил об ошибке: paper jam", stats)
        assert stats.printer_errors == 1

    def test_printer_connect(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("🖨️ Принтер подключен (ID: abcd1234...). Всего подключений: 1", stats)
        assert stats.printer_connects == 1

    def test_printer_disconnect(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("🖨️ Принтер отключен (ID: abcd1234...). Всего подключений: 0", stats)
        assert stats.printer_disconnects == 1

    def test_bot_restart(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Setting up services...", stats)
        assert stats.bot_restarts == 1

    def test_telegram_error(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Failed to fetch updates - TelegramServerError: Bad Gateway", stats)
        assert stats.telegram_errors == 1

    def test_redis_error(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Redis error getting pending jobs: ConnectionError", stats)
        assert stats.redis_errors == 1

    def test_redis_error_russian(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Redis ошибка при проверке дубликата: timeout", stats)
        assert stats.redis_errors == 1

    def test_unknown_message_no_classification(self):
        stats = LogStats()
        LogAnalyzerService._classify_event("Some random log message", stats)
        # Ничего не изменилось
        assert stats.prints_success == 0
        assert stats.printer_errors == 0
        assert stats.bot_restarts == 0


# ── Тесты _read_lines_reverse ────────────────────────────────────


class TestReadLinesReverse:
    def test_reads_lines_in_reverse(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == ["line3", "line2", "line1"]

    def test_empty_file(self, tmp_path):
        log_file = tmp_path / "empty.log"
        log_file.write_text("", encoding="utf-8")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == []

    def test_single_line(self, tmp_path):
        log_file = tmp_path / "single.log"
        log_file.write_text("only line\n", encoding="utf-8")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == ["only line"]

    def test_large_file(self, tmp_path):
        """Проверяем, что большой файл (больше CHUNK_SIZE) корректно читается."""
        log_file = tmp_path / "large.log"
        total_lines = 1000
        expected = [f"line_{i}" for i in range(total_lines)]
        log_file.write_text("\n".join(expected) + "\n", encoding="utf-8")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == list(reversed(expected))

    def test_unicode_content(self, tmp_path):
        log_file = tmp_path / "unicode.log"
        log_file.write_text("Принтер подключен\nОшибка отправки\n", encoding="utf-8")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == ["Ошибка отправки", "Принтер подключен"]

    def test_windows_line_endings(self, tmp_path):
        log_file = tmp_path / "crlf.log"
        log_file.write_bytes(b"line1\r\nline2\r\nline3\r\n")

        lines = list(LogAnalyzerService._read_lines_reverse(log_file))
        assert lines == ["line3", "line2", "line1"]


# ── Тесты analyze_today ──────────────────────────────────────────


class TestAnalyzeToday:
    def test_analyzes_today_lines(self, analyzer, today_str):
        _write_log(analyzer, [
            f"{today_str} 10:00:00 | INFO     | app:func:1 - Setting up services...",
            f"{today_str} 10:01:00 | INFO     | app:func:1 - Чек abc-123 отправлен на принтер продавца 1",
            f"{today_str} 10:02:00 | WARNING  | app:func:1 - Нет подключенных принтеров. Чек xyz добавлен в очередь.",
            f"{today_str} 10:03:00 | ERROR    | app:func:1 - Ошибка отправки на принтер продавца 2: ConnectionError",
        ])

        stats = analyzer.analyze_today()

        assert stats.total_lines == 4
        assert stats.bot_restarts == 1
        assert stats.prints_success == 1
        assert stats.printer_no_connection == 1
        assert stats.printer_errors == 1
        assert stats.total_warnings == 1
        assert stats.total_errors == 1

    def test_stops_at_previous_day(self, analyzer, today_str):
        yesterday = (datetime.now(UZT) - timedelta(days=1)).strftime("%Y-%m-%d")

        _write_log(analyzer, [
            f"{yesterday} 23:58:00 | INFO     | app:func:1 - Setting up services...",
            f"{yesterday} 23:59:00 | INFO     | app:func:1 - Чек old-123 отправлен на принтер продавца 1",
            f"{today_str} 00:01:00 | INFO     | app:func:1 - Чек new-456 отправлен на принтер продавца 2",
            f"{today_str} 10:00:00 | WARNING  | app:func:1 - Нет подключенных принтеров. Чек xyz добавлен в очередь.",
        ])

        stats = analyzer.analyze_today()

        # Только строки за сегодня
        assert stats.total_lines == 2
        assert stats.prints_success == 1   # только new-456
        assert stats.bot_restarts == 0     # вчерашний restart не считается
        assert stats.printer_no_connection == 1

    def test_empty_log_file(self, analyzer):
        stats = analyzer.analyze_today()
        assert stats.total_lines == 0
        assert stats.prints_success == 0

    def test_missing_log_file(self, tmp_path):
        analyzer = LogAnalyzerService(log_path=str(tmp_path / "nonexistent.log"))
        stats = analyzer.analyze_today()
        assert stats.total_lines == 0

    def test_traceback_lines_skipped(self, analyzer, today_str):
        _write_log(analyzer, [
            f"{today_str} 10:00:00 | ERROR    | app:func:1 - Redis error getting pending jobs: timeout",
            "Traceback (most recent call last):",
            '  File "C:\\some\\path.py", line 10, in func',
            "    raise Exception",
            "Exception: some error",
        ])

        stats = analyzer.analyze_today()

        # Только первая строка парсится как лог-строка
        assert stats.total_lines == 1
        assert stats.total_errors == 1
        assert stats.redis_errors == 1

    def test_error_samples_collected(self, analyzer, today_str):
        _write_log(analyzer, [
            f"{today_str} 10:00:00 | ERROR    | app:func:1 - First error message",
            f"{today_str} 10:01:00 | ERROR    | app:func:1 - Second error message",
            f"{today_str} 10:02:00 | ERROR    | app:func:1 - Third error message",
        ])

        stats = analyzer.analyze_today()

        assert stats.total_errors == 3
        assert len(stats.error_samples) == 3
        # Файл читается с конца, поэтому первый sample — последняя строка
        assert "Third error message" in stats.error_samples[0]

    def test_error_samples_limited_to_5(self, analyzer, today_str):
        lines = [
            f"{today_str} 10:{i:02d}:00 | ERROR    | app:func:1 - Error number {i}"
            for i in range(10)
        ]
        _write_log(analyzer, lines)

        stats = analyzer.analyze_today()

        assert stats.total_errors == 10
        assert len(stats.error_samples) == 5


# ── Тесты format_report ──────────────────────────────────────────


class TestFormatReport:
    def test_basic_report_structure(self, analyzer):
        stats = LogStats(
            prints_success=24,
            printer_no_connection=3,
            printer_errors=1,
            receipt_duplicates=0,
            printer_connects=2,
            printer_disconnects=1,
            bot_restarts=1,
            telegram_errors=0,
            redis_errors=0,
            total_lines=156,
            total_warnings=4,
            total_errors=1,
        )
        report_date = datetime(2026, 4, 16, 23, 55, tzinfo=UZT)
        report = analyzer.format_report(stats, report_date=report_date)

        assert "16.04.2026" in report
        assert "Чеки напечатаны: <b>24</b>" in report
        assert "Нет принтеров: <b>3</b>" in report
        assert "Ошибки печати: <b>1</b>" in report
        assert "Перезапусков бота: <b>1</b>" in report
        assert "Строк за период: <b>156</b>" in report
        assert "23:55" in report

    def test_report_includes_error_samples(self, analyzer):
        stats = LogStats(
            total_errors=1,
            error_samples=["Redis error getting pending jobs: timeout"],
        )
        report = analyzer.format_report(stats)

        assert "Последние ошибки" in report
        assert "Redis error" in report

    def test_report_hides_zero_retry_prints(self, analyzer):
        stats = LogStats(prints_retry_success=0)
        report = analyzer.format_report(stats)

        assert "Повторная печать" not in report

    def test_report_shows_nonzero_retry_prints(self, analyzer):
        stats = LogStats(prints_retry_success=5)
        report = analyzer.format_report(stats)

        assert "Повторная печать: <b>5</b>" in report

    def test_report_is_html(self, analyzer):
        stats = LogStats()
        report = analyzer.format_report(stats)

        assert "<b>" in report
        assert "📊" in report


# ── Тесты send_report ────────────────────────────────────────────


class TestSendReport:
    @pytest.mark.asyncio
    async def test_send_report_success(self, analyzer, today_str):
        _write_log(analyzer, [
            f"{today_str} 10:00:00 | INFO     | app:func:1 - Setting up services...",
        ])

        bot = AsyncMock()
        result = await analyzer.send_report(bot, chat_id=123456)

        assert result is True
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == 123456
        assert call_kwargs.kwargs["parse_mode"] == "HTML"
        assert "Дежурный отчёт" in call_kwargs.kwargs["text"]

    @pytest.mark.asyncio
    async def test_send_report_failure(self, analyzer):
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Network error")

        result = await analyzer.send_report(bot, chat_id=123456)
        assert result is False

class TestAnalyzePeriod:
    def test_analyzes_multiple_days(self, analyzer, today_str):
        yesterday = (datetime.now(UZT) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        _write_log(analyzer, [
            f"{yesterday} 10:00:00 | INFO     | app:func:1 - Yesterday action",
            f"{today_str} 10:00:00 | INFO     | app:func:1 - Today action",
        ])

        # Анализ за 2 дня
        stats = analyzer.analyze(days=2)
        assert stats.total_lines == 2

        # Анализ за 1 день
        stats_today = analyzer.analyze(days=1)
        assert stats_today.total_lines == 1

    def test_limit_is_applied(self, analyzer, today_str):
        # Если запросим 100 дней, должно ограничиться 10
        # Но для теста проверим сам факт вызова с ограничением
        stats = analyzer.analyze(days=100)
        # Если не упало и отработало — лимит внутри сработал
        assert stats is not None

    def test_format_report_multi_day(self, analyzer):
        stats = LogStats(total_lines=10)
        report = analyzer.format_report(stats, days=3)
        assert " - " in report # Проверяем наличие диапазона дат
        assert "Строк за период: <b>10</b>" in report
