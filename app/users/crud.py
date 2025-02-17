from typing import cast

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User
from users.schemas import UserCreate, UserList
from utils import get_password_hash


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Retrieve user by email."""
    user = await session.exec(select(User).where(User.email == email))
    return cast(User | None, user.unique().one_or_none())


async def get_user_by_id(session: AsyncSession, id_: int) -> User | None:
    """Retrieve user by ID."""
    user = await session.exec(select(User).where(User.id == id_))
    return cast(User | None, user.unique().one_or_none())


async def get_users(session: AsyncSession, offset: int = 0, limit: int = 100) -> UserList:
    """Retrieve users."""
    count = await session.exec(select(func.count()).select_from(User))
    users = await session.exec(select(User).offset(offset).limit(limit))
    return UserList(count=count.one(), data=users.all())


async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    """Create a new user."""
    user = User.model_validate(user_data, update={"hashed_password": get_password_hash(user_data.password)})
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return cast(User, user)


async def set_user_super(session: AsyncSession, user: User) -> User:
    """Set user as superuser."""
    user.is_superuser = True
    await session.flush()
    await session.refresh(user)
    return user


async def remove_user(session: AsyncSession, user: User) -> None:
    """Remove existed user."""
    await session.delete(user)
