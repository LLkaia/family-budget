import hashlib
import secrets
from datetime import date, datetime
from enum import Enum

from passlib.context import CryptContext
from zoneinfo import ZoneInfo


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PeriodFrom(str, Enum):
    """Period from which start filter data."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"

    def get_date_start(self) -> date:
        """Get date for filter."""
        now = date.today()
        if self == PeriodFrom.DAY:
            return now
        elif self == PeriodFrom.MONTH:
            return date(now.year, now.month, 1)
        elif self == PeriodFrom.YEAR:
            return date(now.year, 1, 1)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed password.

    :param plain_password: plaintext password
    :param hashed_password: hashed password
    :return: True if successful, False otherwise
    """
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Get password hash.

    :param password: plaintext password
    :return: hashed password
    """
    return str(pwd_context.hash(password))


def create_refresh_token() -> str:
    """Generate refresh token."""
    return secrets.token_urlsafe(64)


def get_token_hash(token: str) -> str:
    """Get token's hash."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_datetime_now(timezone: str = "UTC") -> datetime:
    """Get current datetime object.

    If function called with <timezone> parameter,
    return current datetime object for given timezone,
    else return datetime object for UTC.

    :param timezone: timezone string
    :return: datetime object
    """
    return datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
