from enum import Enum


class StockTransactionType(str, Enum):
    """Stock Transaction Types Enum."""

    stock_open = "stock_open"
    stock_close = "stock_close"
    dividends = "dividends"
    cash_in = "cash_in"
    cash_out = "cash_out"
