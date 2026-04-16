from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings
from app.database.models import UserRole
from app.services.user_service import UserService

import logging

logger = logging.getLogger(__name__)


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
                admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip().isdigit()]
                default_role = UserRole.ADMIN if user_id in admin_ids else UserRole.PENDING
                
                # Retrieve or create user in DB — wrapped for safety
                try:
                    user, created = await user_service.get_or_create_user(user_id, username, default_role)
                except Exception as e:
                    logger.exception(f"Auth middleware: failed to get/create user {user_id}")
                    user, created = None, False

                # If DB is down, user is None — respond and bail
                if user is None:
                    if isinstance(event, Message):
                        await event.answer("⚠️ Serverda vaqtinchalik nosozlik. Keyinroq urinib ko'ring.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⚠️ Serverda vaqtinchalik nosozlik.", show_alert=True)
                    return
                
                # If user exists but is in ADMIN_IDS and not ADMIN, auto-promote
                if not created and user.role != UserRole.ADMIN and user_id in admin_ids:
                    try:
                        user = await user_service.update_user_role(user_id, UserRole.ADMIN)
                    except Exception as e:
                        logger.exception(f"Auth middleware: failed to promote user {user_id}")
                
                # Notify admin if someone new registered as PENDING
                if created and user.role == UserRole.PENDING:
                    from app.telegram.keyboards.admin import approve_user_kb
                    text = f"👤 <b>Yangi ruxsat so'rovi!</b>\nFoydalanuvchi: @{user.username or 'username_yoq'}\nID: {user.tg_id}"
                    for admin_id in admin_ids:
                        try:
                            await event.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=approve_user_kb(user.tg_id))
                        except Exception as e:
                            logger.error(f"Failed to send alert to admin {admin_id}: {e}")
                
                # Role barrier
                if user.role == UserRole.BANNED:
                    if isinstance(event, Message) and event.text == "/start":
                        try:
                            await user_service.update_user_role(user.tg_id, UserRole.PENDING)
                            user.role = UserRole.PENDING
                            from app.telegram.keyboards.admin import approve_user_kb
                            text = f"👤 <b>Ruxsat uchun qayta so'rov!</b>\nFoydalanuvchi: @{user.username or 'username_yoq'}\nID: {user.tg_id}"
                            for admin_id in admin_ids:
                                try:
                                    await event.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=approve_user_kb(user.tg_id))
                                except Exception as e:
                                    logger.error(f"Failed to send alert to admin {admin_id}: {e}")
                        except Exception as e:
                            logger.exception(f"Auth middleware: failed to re-request access for {user.tg_id}")
                        await event.answer("⏳ Sizning so'rovingiz qayta ko'rib chiqish uchun yuborildi. Administrator tasdiqlashini kuting.")
                    else:
                        if isinstance(event, Message):
                            await event.answer("🚫 Sizda ruxsat yo'q. Yangi so'rov yuborish uchun /start ni bosing.")
                        elif isinstance(event, CallbackQuery):
                            await event.answer("🚫 Ruxsat etilmagan.", show_alert=True)
                    return
                elif user.role == UserRole.PENDING:
                    if isinstance(event, Message):
                        await event.answer("⏳ Sizning so'rovingiz ko'rib chiqilmoqda. Administrator tasdiqlashini kuting.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳ Sizning so'rovingiz moderatsiyada.", show_alert=True)
                    return
                
                # Pass the db user object to the handler if passed the barrier
                data["db_user"] = user

        return await handler(event, data)
