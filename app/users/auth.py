from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext

from core.config import get_settings
from exceptions import CredentialsException
from users.crud import get_user_by_email
from users.models import User


app_config = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed password.

    Args:
        plain_password: plaintext password
        hashed_password: hashed password
    Returns:
        bool: True if successful, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Get password hash.

    Args:
        password: plaintext password
    Returns:
        str: hashed password
    """
    return pwd_context.hash(password)


async def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate user by email and password.

    Args:
        email: email address to authenticate
        password: password to authenticate
    Returns:
        User: if user exists and authenticated
        None: otherwise
    """
    user = await get_user_by_email(email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_access_token(user: User) -> str:
    """Create access JWT token.

    Args:
        user: User instance
    Returns:
        str: access JWT token
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=app_config.access_token_expire_minutes)
    to_encode = {"exp": expire, "sub": user.email}
    encoded_jwt = jwt.encode(to_encode, app_config.secret_key, algorithm=app_config.algorithm)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """Verify that the token is valid for user.

    Attributes:
        token: JWT access token
    Returns:
        User: if token valid
    Raises:
        CredentialsException: if token expired
    """
    try:
        payload = jwt.decode(token, app_config.secret_key, algorithms=[app_config.algorithm])
    except InvalidTokenError:
        raise CredentialsException
    email = payload.get("sub")
    if email is None:
        raise CredentialsException
    user = await get_user_by_email(email)
    if user is None:
        raise CredentialsException
    expires = payload.get("exp")
    if not expires or expires <= datetime.now(timezone.utc):
        raise CredentialsException("Token expired")
    return user
