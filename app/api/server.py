import uvicorn
from fastapi import FastAPI
from app.config import settings
from app.container import Container
from app.api.routers import example
from app.api.printer_manager import PrinterConnectionManager

def create_app(container: Container, bot=None, dp=None, printer_manager: PrinterConnectionManager = None) -> FastAPI:
    app = FastAPI()
    app.state.container = container
    app.state.bot = bot
    app.state.dp = dp
    
    # Инициализация менеджера принтеров
    if printer_manager is None:
        printer_manager = PrinterConnectionManager()
    app.state.printer_manager = printer_manager
    
    from app.api.routers import example, stats, printer
    app.include_router(example.router)
    app.include_router(stats.router)
    app.include_router(printer.router)
    
    if bot and dp and settings.WEBHOOK_URL:
        from aiogram import types
        import logging
        log = logging.getLogger("webhook")
        
        @app.post(settings.WEBHOOK_PATH)
        async def bot_webhook(update: dict):
            telegram_update = types.Update(**update)
            await dp.feed_update(bot=bot, update=telegram_update)
            return {"status": "ok"}
            
        @app.on_event("startup")
        async def on_startup():
            webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
            log.info(f"Setting webhook to {webhook_url}")
            await bot.set_webhook(webhook_url, drop_pending_updates=True)
            
        @app.on_event("shutdown")
        async def on_shutdown():
            log.info("Deleting webhook and closing bot session")
            await bot.delete_webhook()
            await bot.session.close()

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
