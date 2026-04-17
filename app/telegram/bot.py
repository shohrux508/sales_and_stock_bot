from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.container import Container
from app.telegram.routers import admin, tech, worker


def create_bot_and_dp(container: Container):
    bot = Bot(token=settings.BOT_TOKEN)

    if settings.REDIS_URL:
        storage = RedisStorage.from_url(settings.REDIS_URL)
        dp = Dispatcher(storage=storage)
    else:
        dp = Dispatcher(storage=MemoryStorage())

    # Pass the container into the Dispatcher to bypass globals
    dp["container"] = container

    # Setup middlewares
    from app.telegram.middlewares.auth import AuthMiddleware

    auth_middleware = AuthMiddleware()
    dp.message.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(auth_middleware)

    # Include routers
    dp.include_router(admin.router)
    dp.include_router(worker.router)
    dp.include_router(tech.router)

    return bot, dp


async def start_telegram_polling(bot: Bot, dp: Dispatcher):
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
