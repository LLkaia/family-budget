from typing import cast

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed password.

    :param plain_password: plaintext password
    :param hashed_password: hashed password
    :return: True if successful, False otherwise
    """
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Get password hash.

    :param password: plaintext password
    :return: hashed password
    """
    return cast(str, pwd_context.hash(password))
