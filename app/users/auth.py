import uuid
from datetime import datetime, timedelta
from typing import Annotated, cast

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings
from core.database import get_db
from exceptions import CredentialsException
from models import User
from users.crud import get_user_by_email
from users.schemas import TokenPayload
from utils import get_datatime_now, verify_password


app_config = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/account/login")

# move to Redis later
token_blocklist = set()


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
    expire = get_datatime_now() + timedelta(minutes=app_config.access_token_expire_minutes)
    to_encode = {"exp": expire, "sub": user.email, "jti": str(uuid.uuid1())}
    encoded_jwt = jwt.encode(to_encode, app_config.secret_key, algorithm=app_config.algorithm)
    return cast(str, encoded_jwt)


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
    if not expires or expires.replace(tzinfo=None) <= get_datatime_now() or unic_id in token_blocklist:
        raise CredentialsException("Token has expired")
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


async def destroy_token(token_payload: Annotated[TokenPayload, Depends(decode_access_token)]) -> None:
    """Add token to blocklist by unic identifier.

    :param token_payload: JWT access token payload
    """
    token_blocklist.add(token_payload.jti)
