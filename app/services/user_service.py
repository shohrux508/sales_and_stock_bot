from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from typing import Sequence
import logging

from app.database.models import User, UserRole

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_or_create_user(self, tg_id: int, username: str | None, default_role: UserRole = UserRole.PENDING) -> tuple[User, bool]:
        """Get an existing user or create a new one. Returns tuple(User, is_created)."""
        try:
            async with self.session_maker() as session:
                stmt = select(User).where(User.tg_id == tg_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                created = False
                if not user:
                    logger.info(f"Creating new user {tg_id} with role {default_role.name}")
                    user = User(tg_id=tg_id, username=username, role=default_role)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    created = True
                
                return user, created
        except SQLAlchemyError as e:
            logger.exception(f"DB error in get_or_create_user({tg_id})")
            return None, False

    async def get_user_by_tg_id(self, tg_id: int) -> User | None:
        try:
            async with self.session_maker() as session:
                stmt = select(User).where(User.tg_id == tg_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception(f"DB error in get_user_by_tg_id({tg_id})")
            return None

    async def get_all_users(self) -> Sequence[User]:
        try:
            async with self.session_maker() as session:
                stmt = select(User).order_by(User.id)
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError as e:
            logger.exception("DB error in get_all_users")
            return []
            
    async def update_user_role(self, tg_id: int, role: UserRole) -> User | None:
        try:
            async with self.session_maker() as session:
                stmt = update(User).where(User.tg_id == tg_id).values(role=role).returning(User)
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception(f"DB error in update_user_role({tg_id}, {role})")
            return None

    async def update_user_profile(self, tg_id: int, full_name: str | None = None, phone: str | None = None, is_active: bool | None = None) -> User | None:
        try:
            async with self.session_maker() as session:
                update_data = {}
                if full_name is not None: update_data["full_name"] = full_name
                if phone is not None: update_data["phone"] = phone
                if is_active is not None: update_data["is_active"] = 1 if is_active else 0
                
                if not update_data:
                    # Nothing to update, just fetch
                    stmt = select(User).where(User.tg_id == tg_id)
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none()

                stmt = update(User).where(User.tg_id == tg_id).values(**update_data).returning(User)
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception(f"DB error in update_user_profile({tg_id})")
            return None

    async def update_user_kpi(self, tg_id: int, kpi: int) -> User | None:
        try:
            async with self.session_maker() as session:
                stmt = update(User).where(User.tg_id == tg_id).values(kpi=kpi).returning(User)
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception(f"DB error in update_user_kpi({tg_id}, {kpi})")
            return None
