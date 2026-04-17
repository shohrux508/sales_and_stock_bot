import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.printer_manager import PrinterConnectionManager
from app.config import settings
from app.container import Container

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    bot = app.state.bot
    dp = app.state.dp
    if bot and dp and settings.WEBHOOK_URL:
        try:
            webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
            logger.info(f"Setting webhook to {webhook_url}")
            await bot.set_webhook(webhook_url, drop_pending_updates=True)
        except Exception:
            logger.exception("Failed to set webhook")

    yield

    # Shutdown logic
    if bot:
        try:
            logger.info("Deleting webhook and closing bot session")
            await bot.delete_webhook()
            await bot.session.close()
        except Exception:
            logger.exception("Error during bot shutdown")

def create_app(container: Container, bot=None, dp=None, printer_manager: PrinterConnectionManager = None) -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store state for lifespan and routers
    app.state.container = container
    app.state.bot = bot
    app.state.dp = dp

    if printer_manager is None:
        printer_manager = PrinterConnectionManager()
    app.state.printer_manager = printer_manager

    # Include routers
    from app.api.routers import printer, stats
    app.include_router(stats.router)
    app.include_router(printer.router)

    # Webhook endpoint for Aiogram
    if bot and dp and settings.WEBHOOK_URL:
        from aiogram import types
        @app.post(settings.WEBHOOK_PATH)
        async def bot_webhook(update: dict):
            telegram_update = types.Update(**update)
            await dp.feed_update(bot=bot, update=telegram_update)
            return {"status": "ok"}

    return app

async def start_api(container: Container, bot=None, dp=None, printer_manager=None):
    app = create_app(container, bot, dp, printer_manager)
    config = uvicorn.Config(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()
