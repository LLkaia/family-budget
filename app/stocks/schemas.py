from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from validators import CurrencyValue


class AccountTransactionType(str, Enum):
    """Account Transaction Types Enum."""

    DIVIDENDS = "dividends"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"


class StockSymbolType(str, Enum):
    """Stock Symbol Types Enum."""

    COMMON_STOCK = "Common Stock"
    PREFERENCE = "Preference"
    FOREIGN_SHARE = "Foreign Sh."
    SAVINGS_SHARE = "Savings Share"
    SDR = "SDR"
    ETP = "ETP"
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    NY_REG_SHRS = "NY Reg Shrs"
    ADR = "ADR"
    GDR = "GDR"
    RECEIPT = "Receipt"
    LTD_PART = "Ltd Part"
    MISC = "Misc."
    OPEN_END_FUND = "Open-End Fund"
    CLOSED_END_FUND = "Closed-End Fund"
    UNIT = "Unit"
    REIT = "REIT"
    TRACKING_STOCK = "Tracking Stk"
    DUTCH_CERT = "Dutch Cert"
    ROYALTY_TRUST = "Royalty Trst"
    MLP = "MLP"
    STAPLED_SECURITY = "Stapled Security"
    NVDR = "NVDR"
    CDI = "CDI"
    RIGHT = "Right"
    EQUITY_WRT = "Equity WRT"
    UNKNOWN = ""


class StockAccountCreate(SQLModel):
    """Stock Account Create schema."""

    balance: CurrencyValue = Field(ge=0, description="Current account balance.")
    account_name: str = Field(max_length=255, description="Account name.")


class StockPositionBase(SQLModel):
    """Stock Position Base schema."""

    stock_symbol_id: int
    count: int = Field(gt=0, description="Count of stocks.")
    price_per_stock: CurrencyValue = Field(gt=0, description="Price per one stock.")
    paid_fee: CurrencyValue = Field(ge=0, description="Paid fee per transaction.")


class StockPositionOpen(StockPositionBase):
    """Stock Position Open schema."""

    datetime_opened: datetime = Field(description="When position was opened. Format: 'YYYY-MM-DD HH:MM:SS'")


class StockPositionClose(StockPositionBase):
    """Stock Position Close schema."""

    datetime_closed: datetime = Field(description="When position was closed. Format: 'YYYY-MM-DD HH:MM:SS'")


class StockPositionPublic(SQLModel):
    """Stock Position Public schema."""

    id: int
    account_id: int
    stock_symbol: "StockSymbolPublic"
    datetime_opened: datetime = Field(description="When position was opened.")
    count_active: int = Field(gt=0, description="Count of stocks active.")
    price_per_stock_in: CurrencyValue = Field(gt=0, description="Price per stock in.")


class StockPositionWithCurrentPrice(StockPositionPublic):
    """Stock Position With Current Price schema."""

    current_price: CurrencyValue = Field(ge=0, description="Near real-time stock price.")


class AccountTransactionData(SQLModel):
    """Account Transaction Data schema."""

    datetime_performed: datetime
    account_id: int
    total_amount: CurrencyValue = Field(gt=0)
    transaction_type: AccountTransactionType
    price_per_item: CurrencyValue = Field(gt=0)
    count_items: int = Field(ge=0)
    paid_fee: CurrencyValue = Field(ge=0, default=0)
    taxes_to_pay: CurrencyValue = Field(ge=0, default=0)
    stock_symbol_id: int
    stock_position_id: int = Field(default=None)


class StockSymbolPublic(SQLModel):
    """Stock Symbols public schema."""

    id: int
    figi: str = Field(min_length=12, max_length=12, description="Global unique identifier.")
    symbol: str = Field(min_length=1, max_length=6)
    exchange_code: str = Field(min_length=1, max_length=3, description="Stock exchange identifier.")
    description: str = Field(max_length=255)


class StockSymbolList(SQLModel):
    """List Stock Symbol schema."""

    data: list[StockSymbolPublic]
    count: int


class StockSymbolWithDividendsHistory(StockSymbolPublic):
    """Stock Symbol schema with dividends history."""

    dividends_history: list["DividendPaymentInfo"] | None = Field(default=None)


class DividendPaymentInfo(SQLModel):
    """Dividends Payment Info Schema."""

    amount: CurrencyValue = Field(gt=0)
    payment_date: date
