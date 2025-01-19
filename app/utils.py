from datetime import date, datetime, timedelta
from enum import Enum

import finnhub
from passlib.context import CryptContext
from zoneinfo import ZoneInfo

from core.config import get_settings
from core.redis import RedisKeys, redis_client


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

finnhub_client = finnhub.Client(api_key=get_settings().finnhub_api_key)


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


async def get_stock_price_now(ticket: str, cache_ttl: int = 86400, update_after: int = 3600) -> float:
    """Get stock price by ticket.

    Get stock price by <ticket> from cache if it is there and
    <update_after> seconds not reached since last cache update,
    otherwise try to update price data by calling finnhub API.
    If data missed in cache, call finnhub API. Cache price data
    after each successful API call with <cache_ttl> seconds TTL.
    Return <None> if no info in cache and finnhub API is throttled.

    :param ticket: Ticket name (e.g. AAPL)
    :param cache_ttl: TTL for row in redis (24 hours by default)
    :param update_after: number of seconds after which try to
        update cache (1 hour by default)
    :return: stock price or None
    """
    current_timestamp = int(get_datatime_now().timestamp())

    data_from_cache = await redis_client.read_row_from_cache(RedisKeys.stock_price.value, ticket)
    price_from_cache = "0"

    # return cached price if cache created lt <update_after> seconds ago
    if data_from_cache:
        price_from_cache, timestamp = data_from_cache.split(";")
        if current_timestamp - int(timestamp) < update_after:
            return float(price_from_cache)

    # try to get fresh data, otherwise return cached price or 0
    try:
        retrieved_data = finnhub_client.quote(ticket)
    except finnhub.FinnhubAPIException:  # 429 throttle error
        return float(price_from_cache)

    # current price could be 0 if ticket name is incorrect, skip caching
    current_price = retrieved_data["c"]
    if current_price > 0:
        await redis_client.add_row_to_cache(
            redis_key=RedisKeys.stock_price.value,
            key=ticket,
            value=f"{current_price};{current_timestamp}",
            ttl=timedelta(seconds=cache_ttl),
        )

    return float(current_price)
