from aiogram import Router, types, F
from aiogram.filters import Command
import re
import logging

from app.config import settings
from app.container import Container
from app.services.log_analyzer import LogAnalyzerService

logger = logging.getLogger(__name__)
router = Router()

# Filter: only TECH_ADMIN_ID can use this router
router.message.filter(lambda message: message.from_user.id == settings.TECH_ADMIN_ID)

@router.message(F.text.regexp(r"^/tech_report:(\d+)$"))
async def cmd_tech_report_forced(message: types.Message, container: Container):
    """
    Forced log report with custom days.
    Usage: /tech_report:7
    """
    match = re.match(r"^/tech_report:(\d+)$", message.text)
    if not match:
        return
    
    days = int(match.group(1))
    log_analyzer: LogAnalyzerService = container.get("log_analyzer")
    
    status_msg = await message.answer(f"⏳ Формирую отчёт за {days} дн...")
    
    success = await log_analyzer.send_report(
        bot=message.bot,
        chat_id=message.chat.id,
        days=days
    )
    
    await status_msg.delete()
    if not success:
        await message.answer("❌ Ошибка при генерации отчёта. Проверьте логи.")

@router.message(Command("tech_report"))
async def cmd_tech_report_help(message: types.Message):
    """Fallback help for tech_report command."""
    await message.answer(
        "Использование: <code>/tech_report:число</code>\n"
        "Например: <code>/tech_report:7</code> (макс. 10 дней)",
        parse_mode="HTML"
    )
