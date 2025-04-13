import uuid
from datetime import timedelta
from typing import Annotated, cast

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings
from core.database import get_db
from core.redis import redis_client
from exceptions import CredentialsException
from models import Session, User
from users.crud import create_session, get_session_by_token_hash, get_user_by_email, revoke_session_by_token_hash
from users.schemas import TokenPayload
from utils import create_refresh_token, get_datetime_now, get_token_hash, verify_password


app_config = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/account/login")


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate user by email and password.

    :param session: DB session
    :param email: email address to authenticate
    :param password: password to authenticate
    :return: User if exists and authenticated else None
    """
    user = await get_user_by_email(session, email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_access_token(user: User) -> str:
    """Create access JWT token.

    :param user: User instance
    :return: access JWT token
    """
    expire = get_datetime_now() + timedelta(minutes=app_config.access_token_expire_minutes)
    to_encode = {"exp": expire, "sub": user.email, "jti": str(uuid.uuid4())}
    encoded_jwt = jwt.encode(to_encode, app_config.secret_key, algorithm=app_config.algorithm)
    return cast(str, encoded_jwt)


async def create_new_session_for_user(session: AsyncSession, user: User, request: Request, response: Response) -> None:
    """Create new session for user.

    :param session: DB session
    :param user: User instance
    :param request: Request instance
    :param response: Response instance
    """
    refresh_token = create_refresh_token()
    datetime_now = get_datetime_now()

    await create_session(
        session=session,
        user_id=user.id,
        user_agent=request.headers.get("user-agent", ""),
        refresh_token_hash=get_token_hash(refresh_token),
        ip_address=request.client.host,
        created_at=datetime_now,
        expires_at=datetime_now + timedelta(minutes=app_config.refresh_token_expire_minutes),
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=app_config.refresh_token_expire_minutes * 60,
        path="/account",
    )


async def verify_session(session: AsyncSession, request: Request) -> Session:
    """Verify and retrieve user session."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise CredentialsException("Missing refresh token")
    refresh_token_hash = get_token_hash(refresh_token)

    user_session = await get_session_by_token_hash(session, refresh_token_hash)
    if not user_session:
        raise CredentialsException
    if user_session.revoked:
        raise CredentialsException
    if user_session.expires_at < get_datetime_now():
        raise CredentialsException("Refresh token expired")

    return user_session


def decode_access_token(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenPayload:
    """Decode access token.

    :param token: JWT access token
    :return: decoded JWT access token payload
    """
    try:
        payload = jwt.decode(token, app_config.secret_key, algorithms=[app_config.algorithm])
    except InvalidTokenError:
        raise CredentialsException
    return TokenPayload(**payload)


async def current_user(
    token_payload: Annotated[TokenPayload, Depends(decode_access_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Verify that the token is valid for user.

    :param token_payload: JWT access token payload
    :param session: DB session
    :return: User if token valid
    """
    expires = token_payload.exp
    unic_id = token_payload.jti
    if (
        not expires
        or expires.replace(tzinfo=None) <= get_datetime_now()
        or await redis_client.is_token_blacklisted(unic_id)
    ):
        raise CredentialsException
    email = token_payload.sub
    if email is None:
        raise CredentialsException
    user = await get_user_by_email(session, email)
    if user is None:
        raise CredentialsException
    return user


def current_superuser(user: Annotated[User, Depends(current_user)]) -> User:
    """Verify that verified user is superuser.

    :param user: verified user
    :return: user if superuser
    """
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return user


async def destroy_tokens(
    request: Request,
    response: Response,
    token_payload: Annotated[TokenPayload, Depends(decode_access_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Destroy access and refresh tokens.

    :param request: Request instance
    :param response: Response instance
    :param token_payload: JWT access token payload
    :param session: DB session
    """
    # remove session by refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_session_by_token_hash(session, get_token_hash(refresh_token))
        response.delete_cookie("refresh_token", path="/")

    # blacklist access token
    ttl = token_payload.exp.replace(tzinfo=None) - get_datetime_now()
    await redis_client.add_token_to_blacklist(token_payload.jti, ttl)
