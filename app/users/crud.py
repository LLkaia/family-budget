from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from users.models import User


async def get_user_by_email(email: str, session: AsyncSession = Depends(get_db)) -> User | None:
    user = await session.exec(select(User).where(User.email == email))
    return user.scalar_one_or_none()


async def get_users(offset: int = 0, limit: int = 100, session: AsyncSession = Depends(get_db)) -> list[User]:
    users = await session.exec(select(User).offset(offset).limit(limit))
    return users.scalars().all()
