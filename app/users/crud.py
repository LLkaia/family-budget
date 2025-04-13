from datetime import datetime
from typing import cast

from sqlalchemy.orm import joinedload
from sqlmodel import and_, case, func, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Session, User
from users.schemas import SessionPublic, UserCreate, UserList
from utils import get_datetime_now, get_password_hash


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


async def create_session(
    session: AsyncSession,
    user_id: int,
    user_agent: str,
    refresh_token_hash: str,
    ip_address: str,
    created_at: datetime,
    expires_at: datetime,
) -> None:
    """Create a new Session.

    :param session: Session instance
    :param user_id: User ID
    :param user_agent: User-Agent
    :param refresh_token_hash: refresh token hash
    :param ip_address: session's IP address
    :param created_at: date n time when session is created
    :param expires_at: date n time when session will expire
    """
    new_session = Session(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=created_at,
        expires_at=expires_at,
    )
    session.add(new_session)


async def get_session_by_token_hash(session: AsyncSession, token_hash: str) -> Session | None:
    """Get session by token's hash."""
    user_session = await session.exec(
        select(Session).where(Session.refresh_token_hash == token_hash).options(joinedload(Session.user))
    )
    return cast(Session | None, user_session.unique().one_or_none())


async def revoke_session_by_token_hash(session: AsyncSession, token_hash: str) -> None:
    """Revoke session by token's hash."""
    await session.exec(update(Session).where(Session.refresh_token_hash == token_hash).values(revoked=True))


async def revoke_user_sessions(session: AsyncSession, user: User, session_id: int | None = None) -> None:
    """Revoke User's sessions."""
    query = update(Session).where(Session.user_id == user.id).values(revoked=True)
    if session_id is not None:
        query = query.where(Session.id == session_id)
    await session.exec(query)


async def get_sessions_by_user_id(session: AsyncSession, user_id: int, is_active: bool) -> list[SessionPublic]:
    """Get user's sessions by user ID."""
    is_active_condition = and_(Session.revoked == False, Session.expires_at > get_datetime_now())  # noqa: E712
    is_active_field = case((is_active_condition, True), else_=False).label("is_active")

    # query sessions and create alias for active sessions
    query = (
        select(Session, is_active_field)
        .where(Session.user_id == user_id)
        .order_by(is_active_field.desc(), Session.created_at.desc())  # type: ignore[attr-defined]
    )

    # retrieve only active sessions
    if is_active is True:
        query = query.where(is_active_condition)

    user_sessions = await session.exec(query)
    return [
        SessionPublic(**user_session.model_dump(), is_active=is_active) for user_session, is_active in user_sessions
    ]
