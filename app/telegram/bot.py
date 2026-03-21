from aiogram import Bot, Dispatcher
from app.config import settings
from app.container import Container
from app.telegram.routers import admin, worker

async def start_telegram(container: Container):
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Pass the container into the Dispatcher to bypass globals
    dp["container"] = container

    # Setup middlewares
    from app.telegram.middlewares.auth import AuthMiddleware
    auth_middleware = AuthMiddleware()
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)

    # Include routers
    dp.include_router(admin.router)
    dp.include_router(worker.router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
