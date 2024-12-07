from enum import Enum


class StockTransactionType(str, Enum):
    """Stock Transaction Types Enum."""

    BUY = "buy"
    SELL = "sell"


class AccountTransactionType(str, Enum):
    """Account Transaction Types Enum."""

    DIVIDENDS = "dividends"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
