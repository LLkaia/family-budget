from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import finnhub
import pytest

from stocks.finnhub import get_latest_stock_price


@pytest.mark.asyncio
@patch("stocks.finnhub.get_datetime_now")
@patch("stocks.finnhub.redis_client")
@patch("stocks.finnhub.get_finnhub_client")
async def test_get_price_from_cache(mock_finnhub: MagicMock, mock_redis: MagicMock, mock_now: MagicMock) -> None:
    mock_redis.read_row_from_cache = AsyncMock(return_value="100.5;1234567890")
    mock_now.return_value.timestamp.return_value = 1234567899

    result = await get_latest_stock_price("AAPL")

    assert result == 100.5
    mock_finnhub.quote.assert_not_called()


@pytest.mark.asyncio
@patch("stocks.finnhub.get_datetime_now")
@patch("stocks.finnhub.redis_client")
@patch("stocks.finnhub.get_finnhub_client")
async def test_get_price_from_fresh_api(mock_finnhub: MagicMock, mock_redis: MagicMock, mock_now: MagicMock) -> None:
    mock_redis.read_row_from_cache = AsyncMock(return_value=None)
    mock_redis.add_row_to_cache = AsyncMock()
    mock_finnhub.return_value.quote.return_value = {"c": 150.75}
    mock_now.return_value.timestamp.return_value = 1234567890

    result = await get_latest_stock_price("AAPL")

    assert result == 150.75
    mock_finnhub.return_value.quote.assert_called_once_with("AAPL")
    mock_redis.add_row_to_cache.assert_called_once_with(
        redis_key="stock_price", key="AAPL", value="150.7500;1234567890", ttl=timedelta(seconds=86400)
    )


@pytest.mark.asyncio
@patch("stocks.finnhub.get_datetime_now")
@patch("stocks.finnhub.redis_client")
@patch("stocks.finnhub.get_finnhub_client")
async def test_finnhub_api_throttling(mock_finnhub: MagicMock, mock_redis: MagicMock, mock_now: MagicMock) -> None:
    mock_redis.read_row_from_cache = AsyncMock(return_value="100.5;1234561111")
    mock_now.return_value.timestamp.return_value = 1234567890
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "error"}
    mock_finnhub.side_effect = finnhub.FinnhubAPIException(mock_response)

    result = await get_latest_stock_price("AAPL")

    assert result == 100.5
    mock_finnhub.assert_called_once()
    mock_redis.read_row_from_cache.assert_called_once_with("stock_price", "AAPL")


@pytest.mark.asyncio
@patch("stocks.finnhub.get_datetime_now")
@patch("stocks.finnhub.redis_client")
@patch("stocks.finnhub.get_finnhub_client")
async def test_invalid_ticket(mock_finnhub: MagicMock, mock_redis: MagicMock, mock_now: MagicMock) -> None:
    mock_redis.read_row_from_cache = AsyncMock(return_value=None)
    mock_now.return_value.timestamp.return_value = 1234567890
    mock_finnhub.return_value.quote.return_value = {"c": 0}

    result = await get_latest_stock_price("INVALID")

    assert result == 0
    mock_finnhub.return_value.quote.assert_called_once_with("INVALID")
    mock_redis.add_row_to_cache.assert_not_called()
