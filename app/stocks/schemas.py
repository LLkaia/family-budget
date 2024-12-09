from enum import Enum

from sqlmodel import Field, SQLModel


class StockTransactionType(str, Enum):
    """Stock Transaction Types Enum."""

    BUY = "buy"
    SELL = "sell"


class AccountTransactionType(str, Enum):
    """Account Transaction Types Enum."""

    DIVIDENDS = "dividends"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class StockAccountCreate(SQLModel):
    """Stock Account Create schema."""

    balance: float = Field(ge=0, description="Current account balance.")
    account_name: str = Field(max_length=255, description="Account name.")
