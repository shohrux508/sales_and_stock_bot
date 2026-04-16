import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str  # Comma-separated list of admin IDs
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    def __init__(self, **values):
        super().__init__(**values)
        import os
        # Railway and other PaaS providers usually provide a PORT env var.
        env_port = os.getenv("PORT")
        if env_port:
            self.API_PORT = int(env_port)
    WEBAPP_URL: str = "https://localhost:8000"
    DASHBOARD_PASSWORD: str = "admin123"
    RUN_TELEGRAM: bool = True
    RUN_API: bool = True
    DATABASE_URL: str = ''
    REDIS_URL: str = "redis://localhost:6379/0"
    PRINTER_SECRET_TOKEN: str = "change-me-to-secure-token"
    WEBHOOK_URL: str = ""
    WEBHOOK_PATH: str = "/webhook"
    TECH_ADMIN_ID: int = 0
    LOG_REPORT_TIME: str = "23:55"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
