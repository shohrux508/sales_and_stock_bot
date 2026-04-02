import asyncio
import logging
from app.config import settings
from app.container import Container
from app.services.user_service import UserService
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService
from app.database.core import async_session_maker

logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        self.container = Container()

    def setup_services(self):
        logger.info("Setting up services...")
        from app.services.example_service import ExampleService
        self.container.register("example_service", ExampleService())
        self.container.register("user_service", UserService(async_session_maker))
        self.container.register("product_service", ProductService(async_session_maker))
        self.container.register("transaction_service", TransactionService(async_session_maker))
        self.container.register("category_service", CategoryService(async_session_maker))


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
            return start_api(self.container, bot, dp)
        return None

    async def run(self):
        self.setup_services()
        
        tasks = []
        
        telegram_task = await self.setup_telegram()
        if telegram_task:
            tasks.append(telegram_task)
            
        api_task = await self.setup_api()
        if api_task:
            tasks.append(api_task)

        if not tasks:
            logger.warning("No components enabled to run (RUN_TELEGRAM=False, RUN_API=False)")
            return

        await asyncio.gather(*tasks)
