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
                user, created = await user_service.get_or_create_user(user_id, username, default_role)
                
                # Notify admin if someone new registered as PENDING
                if created and user.role == UserRole.PENDING:
                    from app.telegram.keyboards.admin import approve_user_kb
                    text = f"👤 *Новая заявка на доступ!*\nПользователь: @{user.username or 'без_юзернейма'}\nID: {user.tg_id}"
                    try:
                        await event.bot.send_message(settings.ADMIN_ID, text, parse_mode="Markdown", reply_markup=approve_user_kb(user.tg_id))
                    except Exception:
                        pass # Ignore if admin didn't start the bot
                
                # Role barrier
                if user.role == UserRole.BANNED:
                    if isinstance(event, Message):
                        await event.answer("🚫 Доступ запрещен администратором.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Доступ запрещен.", show_alert=True)
                    return
                elif user.role == UserRole.PENDING:
                    if isinstance(event, Message):
                        await event.answer("⏳ Ваша заявка находится на рассмотрении. Ожидайте подтверждения от администратора.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳ Ваша заявка на модерации.", show_alert=True)
                    return
                
                # Pass the db user object to the handler if passed the barrier
                data["db_user"] = user

        return await handler(event, data)
