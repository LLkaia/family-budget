from enum import Enum

from sqlmodel import Field, SQLModel


class AccountTransactionType(str, Enum):
    """Account Transaction Types Enum."""

    DIVIDENDS = "dividends"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"


class StockAccountCreate(SQLModel):
    """Stock Account Create schema."""

    balance: float = Field(ge=0, description="Current account balance.")
    account_name: str = Field(max_length=255, description="Account name.")
