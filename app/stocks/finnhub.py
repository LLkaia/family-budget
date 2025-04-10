from datetime import timedelta
from functools import lru_cache

import finnhub

from core.config import get_settings
from core.redis import RedisKeys, redis_client
from models import StockSymbol
from stocks.schemas import StockSymbolType
from utils import get_datetime_now


@lru_cache
def get_finnhub_client() -> finnhub.Client:
    """Get a finnhub client."""
    return finnhub.Client(api_key=get_settings().finnhub_api_key)


async def get_latest_stock_price(ticket: str, cache_ttl: int = 86400, update_after: int = 3600) -> float:
    """Get latest stock price by ticket.

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
    current_timestamp = int(get_datetime_now().timestamp())

    data_from_cache = await redis_client.read_row_from_cache(RedisKeys.stock_price.value, ticket)
    price_from_cache = "0"

    # return cached price if cache created lt <update_after> seconds ago
    if data_from_cache:
        price_from_cache, timestamp = data_from_cache.split(";")
        if current_timestamp - int(timestamp) < update_after:
            return float(price_from_cache)

    # try to get fresh data, otherwise return cached price or 0
    try:
        retrieved_data = get_finnhub_client().quote(ticket)
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


async def get_stock_symbols_data(
    exchange_code: str = "US", type_of_symbols: list[StockSymbolType] | None = None
) -> list[dict[str, str]]:
    """Get stock symbols per stock exchange.

    :param exchange_code: exchange code of needed stock exchange.
    :param type_of_symbols: type of symbols to return.
    :return: list of dicts with stock symbols data.
    """
    exchange_code = exchange_code.upper()
    if type_of_symbols is None:
        type_of_symbols = [StockSymbolType.COMMON_STOCK, StockSymbolType.ETP]

    try:
        requested_data = get_finnhub_client().stock_symbols(exchange_code)
    except finnhub.FinnhubAPIException:  # 429 throttle error
        return []

    # take 'StockSymbol' fields from items in 'requested_data' and extend it with 'extra_data'
    allowed_keys = StockSymbol.__table__.columns
    extra_data = {"exchange_code": exchange_code}

    # additionally, filter only needed types of symbols
    return [
        {**{key: item[key] for key in item if key in allowed_keys}, **extra_data, **{"symbol_type": item["type"]}}
        for item in requested_data
        if item["type"] in type_of_symbols
    ]
