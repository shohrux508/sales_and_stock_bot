import asyncio
import logging
from app.config import settings
from app.container import Container
from app.services.user_service import UserService
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService
from app.services.log_analyzer import LogAnalyzerService
from app.database.core import async_session_maker

logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        self.container = Container()
        self.printer_manager = None
        self.log_analyzer = None

    def setup_services(self):
        logger.info("Setting up services...")
        self.container.register("user_service", UserService(async_session_maker))
        self.container.register("product_service", ProductService(async_session_maker))
        self.container.register("transaction_service", TransactionService(async_session_maker))
        self.container.register("category_service", CategoryService(async_session_maker))

        # Регистрация менеджера принтеров
        from app.api.printer_manager import PrinterConnectionManager
        self.printer_manager = PrinterConnectionManager()
        self.container.register("printer_manager", self.printer_manager)
        logger.info("PrinterConnectionManager зарегистрирован в DI-контейнере")

        # Регистрация Log Analyzer
        self.log_analyzer = LogAnalyzerService()
        self.container.register("log_analyzer", self.log_analyzer)
        logger.info("LogAnalyzerService зарегистрирован в DI-контейнере")

    async def init_printer_redis(self):
        """Инициализация Redis для дедупликации чеков."""
        if self.printer_manager and settings.REDIS_URL:
            await self.printer_manager.init_redis(settings.REDIS_URL)

    async def setup_telegram(self):
        if settings.RUN_TELEGRAM:
            from app.telegram.bot import create_bot_and_dp, start_telegram_polling
            logger.info("Initializing Telegram Bot...")
            bot, dp = create_bot_and_dp(self.container)
            self.bot = bot
            self.dp = dp
            
            # If no webhook is configured, or API is disabled, fallback to polling
            if not settings.RUN_API or not settings.WEBHOOK_URL:
                logger.info("Starting Telegram Bot with Polling...")
                return start_telegram_polling(bot, dp)
            else:
                logger.info("Telegram Bot will run via Webhooks through FastAPI.")
        return None

    async def setup_api(self):
        if settings.RUN_API:
            from app.api.server import start_api
            logger.info("Starting API Server...")
            bot = getattr(self, "bot", None)
            dp = getattr(self, "dp", None)
            return start_api(self.container, bot, dp, self.printer_manager)
        return None

    async def setup_log_analyzer(self):
        """Запуск фоновой задачи Log Analyzer (ежедневный отчёт)."""
        if not settings.TECH_ADMIN_ID:
            logger.warning("TECH_ADMIN_ID не задан — Log Analyzer отключён")
            return None
        if not self.log_analyzer:
            return None

        bot = getattr(self, "bot", None)
        if not bot:
            logger.warning("Bot не инициализирован — Log Analyzer отключён")
            return None

        logger.info(f"Log Analyzer: отчёт будет отправляться в {settings.LOG_REPORT_TIME} → {settings.TECH_ADMIN_ID}")
        return self.log_analyzer.scheduler_loop(
            bot=bot,
            chat_id=settings.TECH_ADMIN_ID,
            report_time=settings.LOG_REPORT_TIME,
        )

    async def run(self):
        self.setup_services()
        
        # Инициализация Redis для принтера
        await self.init_printer_redis()
        
        tasks = []
        
        telegram_task = await self.setup_telegram()
        if telegram_task:
            tasks.append(telegram_task)
            
        api_task = await self.setup_api()
        if api_task:
            tasks.append(api_task)

        log_analyzer_task = await self.setup_log_analyzer()
        if log_analyzer_task:
            tasks.append(log_analyzer_task)

        if not tasks:
            logger.warning("No components enabled to run (RUN_TELEGRAM=False, RUN_API=False)")
            return

        await asyncio.gather(*tasks)

