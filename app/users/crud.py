from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from users.models import User, UserCreate, UsersPublic
from users.utils import get_password_hash


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Retrieve user by email."""
    user = await session.exec(select(User).where(User.email == email))
    return user.one_or_none()


async def get_users(session: AsyncSession, offset: int = 0, limit: int = 100) -> UsersPublic:
    """Retrieve users."""
    count = await session.exec(select(func.count()).select_from(User))
    users = await session.exec(select(User).offset(offset).limit(limit))
    return UsersPublic(count=count.one(), data=users.all())


async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    """Create a new user."""
    user = User.model_validate(user_data, update={"hashed_password": get_password_hash(user_data.password)})
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
