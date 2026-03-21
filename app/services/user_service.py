from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update
from typing import Sequence
import logging

from app.database.models import User, UserRole

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, async_session_maker: async_sessionmaker):
        self.session_maker = async_session_maker

    async def get_or_create_user(self, tg_id: int, username: str | None, default_role: UserRole = UserRole.PENDING) -> tuple[User, bool]:
        """Get an existing user or create a new one. Returns tuple(User, is_created)."""
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

    async def get_user_by_tg_id(self, tg_id: int) -> User | None:
        async with self.session_maker() as session:
            stmt = select(User).where(User.tg_id == tg_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_users(self) -> Sequence[User]:
        async with self.session_maker() as session:
            stmt = select(User).order_by(User.id)
            result = await session.execute(stmt)
            return result.scalars().all()
            
    async def update_user_role(self, tg_id: int, role: UserRole) -> User | None:
        async with self.session_maker() as session:
            user = await self.get_user_by_tg_id(tg_id)
            if user:
                from sqlalchemy import update
                stmt = update(User).where(User.tg_id == tg_id).values(role=role).returning(User)
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one()
            return None
