import asyncio
import logging
from app.config import settings
from app.container import Container
from app.services.user_service import UserService
from app.services.product_service import ProductService
from app.services.transaction_service import TransactionService
from app.database.core import async_session_maker

logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        self.container = Container()

    def setup_services(self):
        logger.info("Setting up services...")
        self.container.register("user_service", UserService(async_session_maker))
        self.container.register("product_service", ProductService(async_session_maker))
        self.container.register("transaction_service", TransactionService(async_session_maker))


    async def setup_telegram(self):
        if settings.RUN_TELEGRAM:
            from app.telegram.bot import start_telegram
            logger.info("Starting Telegram Bot...")
            return start_telegram(self.container)
        return None

    async def setup_api(self):
        if settings.RUN_API:
            from app.api.server import start_api
            logger.info("Starting API Server...")
            return start_api(self.container)
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
