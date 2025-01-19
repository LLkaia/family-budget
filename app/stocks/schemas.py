from datetime import date
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


class StockPositionBase(SQLModel):
    """Stock Position Base schema."""

    date_opened: date = Field(description="When position was opened.")
    ticket_name: str = Field(max_length=10)


class StockPositionOpen(StockPositionBase):
    """Stock Position Open schema."""

    count: int = Field(gt=0, description="Count of stocks bought.")
    price_per_stock: float = Field(gt=0, description="Price per one stock.")
    paid_fee: float = Field(ge=0, description="Paid fee per transaction.")


class StockPositionWithCurrentPrice(StockPositionBase):
    """Stock Position With Current Price schema."""

    id: int
    account_id: int
    count_active: int = Field(gt=0, description="Count of stocks active.")
    price_per_stock_in: float = Field(gt=0, description="Price per stock in.")
    current_price: float = Field(ge=0, description="Near real-time stock price.")
