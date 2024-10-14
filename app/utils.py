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


def get_datatime_now(timezone: str = "UTC") -> datetime:
    """Get current datatime object.

    If function called with <timezone> parameter,
    return current datatime object for given timezone,
    else return datatime object for UTC.

    :param timezone: timezone string
    :return: datatime object
    """
    return datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
