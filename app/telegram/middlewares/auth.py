from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings
from app.database.models import UserRole
from app.services.user_service import UserService

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = None
        username = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username

        if user_id:
            container = data.get("container")
            if container:
                user_service: UserService = container.get("user_service")
                
                # Determine default role depending on config
                default_role = UserRole.ADMIN if user_id == settings.ADMIN_ID else UserRole.WORKER
                
                # Retrieve or create user in DB
                user = await user_service.get_or_create_user(user_id, username, default_role)
                
                # Pass the db user object to the handler
                data["db_user"] = user

        return await handler(event, data)
