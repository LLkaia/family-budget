from datetime import date, datetime
from typing import Any

from pydantic import EmailStr, field_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel, UniqueConstraint, func

from stocks.schemas import AccountTransactionType, StockSymbolType
from utils import get_datetime_now
from validators import CurrencyValue, normalize_name


class UserBudgetLink(SQLModel, table=True):  # type: ignore[call-arg]
    """Link table for User and Budget."""

    user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    budget_id: int = Field(foreign_key="budget.id", primary_key=True, ondelete="CASCADE")


class Budget(SQLModel, table=True):  # type: ignore[call-arg]
    """Budget database model."""

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    balance: CurrencyValue = Field(ge=0, decimal_places=4)

    users: list["User"] = Relationship(back_populates="budgets", link_model=UserBudgetLink)
    categories: list["Category"] = Relationship(back_populates="budget", cascade_delete=True)


class User(SQLModel, table=True):  # type: ignore[call-arg]
    """User database model."""

    id: int = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=255)
    email: EmailStr = Field(unique=True, max_length=255, index=True)
    hashed_password: str = Field(min_length=59, max_length=60)
    telegram_id: int | None = Field(default=None)
    is_superuser: bool = Field(default=False)

    budgets: list[Budget] = Relationship(back_populates="users", link_model=UserBudgetLink)
    stock_accounts: list["StockAccount"] = Relationship(back_populates="owner", cascade_delete=True)
    sessions: list["Session"] = Relationship(back_populates="user", cascade_delete=True)


class Category(SQLModel, table=True):  # type: ignore[call-arg]
    """Category database model."""

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    category_restriction: CurrencyValue = Field(ge=0, decimal_places=4)
    description: str | None = Field(max_length=255)
    is_income: bool
    budget_id: int = Field(foreign_key="budget.id", ondelete="CASCADE")

    budget: Budget = Relationship(back_populates="categories")
    transactions: list["Transaction"] = Relationship(back_populates="category", cascade_delete=True)

    __table_args__ = (UniqueConstraint("budget_id", "name", name="uq_budget_category"),)
    _normalize_name = field_validator("name", mode="before")(normalize_name)


class PredefinedCategory(SQLModel, table=True):  # type: ignore[call-arg]
    """Predefined categories database model."""

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True)

    _normalize_name = field_validator("name", mode="before")(normalize_name)


class Transaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Transaction database model."""

    id: int = Field(default=None, primary_key=True)
    date_performed: date = Field(description="When transaction was performed.")
    amount: CurrencyValue = Field(gt=0, decimal_places=4)
    category_id: int = Field(foreign_key="category.id", ondelete="CASCADE")
    datetime_added: datetime = Field(default_factory=get_datetime_now, description="When transaction was added.")

    category: Category = Relationship(back_populates="transactions")


class StockAccount(SQLModel, table=True):  # type: ignore[call-arg]
    """Stock account database model."""

    id: int = Field(default=None, primary_key=True)
    balance: CurrencyValue = Field(ge=0, decimal_places=4)
    account_name: str = Field(max_length=255)
    owner_id: int = Field(foreign_key="user.id", ondelete="CASCADE")

    owner: User = Relationship(back_populates="stock_accounts")
    stock_positions: list["StockPosition"] = Relationship(back_populates="stock_account", cascade_delete=True)
    account_transactions: list["AccountTransaction"] = Relationship(back_populates="stock_account", cascade_delete=True)


class StockPosition(SQLModel, table=True):  # type: ignore[call-arg]
    """Stock position database model."""

    id: int = Field(default=None, primary_key=True)
    count_active: int = Field(ge=0)
    datetime_opened: datetime = Field(description="When position was opened.")
    account_id: int = Field(foreign_key="stockaccount.id", ondelete="CASCADE")
    price_per_stock_in: CurrencyValue = Field(ge=0, decimal_places=4, description="Price per stock in.")
    stock_symbol_id: int = Field(foreign_key="stocksymbol.id", ondelete="CASCADE")

    transactions: list["AccountTransaction"] = Relationship(back_populates="stock_position", cascade_delete=True)
    stock_account: StockAccount = Relationship(back_populates="stock_positions")
    stock_symbol: "StockSymbol" = Relationship(back_populates="stock_positions")


class AccountTransaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Account Transaction database model."""

    id: int = Field(default=None, primary_key=True)
    datetime_performed: datetime = Field(description="When transaction was performed.")
    account_id: int = Field(foreign_key="stockaccount.id", ondelete="CASCADE")
    total_amount: CurrencyValue = Field(gt=0, decimal_places=4)
    transaction_type: AccountTransactionType
    paid_fee: CurrencyValue = Field(ge=0, decimal_places=4, default=0)
    taxes_to_pay: CurrencyValue = Field(ge=0, decimal_places=4, default=0)
    price_per_item: CurrencyValue = Field(ge=0, decimal_places=4)
    count_items: int = Field(ge=0)
    stock_position_id: int = Field(foreign_key="stockposition.id", default=None, ondelete="CASCADE")
    stock_symbol_id: int = Field(foreign_key="stocksymbol.id", default=None, ondelete="CASCADE")

    stock_account: StockAccount = Relationship(back_populates="account_transactions")
    stock_position: StockPosition = Relationship(back_populates="transactions")
    stock_symbol: "StockSymbol" = Relationship(back_populates="transactions")


class StockSymbol(SQLModel, table=True):  # type: ignore[call-arg]
    """Stock Symbols database model."""

    id: int = Field(default=None, primary_key=True)
    figi: str = Field(min_length=12, max_length=12, unique=True, description="Global unique identifier.")
    symbol: str = Field(min_length=1, max_length=6)
    exchange_code: str = Field(min_length=1, max_length=3, description="Stock exchange identifier.")
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(max_length=255)
    symbol_type: StockSymbolType

    transactions: list[AccountTransaction] = Relationship(back_populates="stock_symbol", cascade_delete=True)
    stock_positions: list[StockPosition] = Relationship(back_populates="stock_symbol", cascade_delete=True)

    __table_args__ = (UniqueConstraint("symbol", "exchange_code", name="uq_symbol_exchange_code"),)


class AuditLog(SQLModel, table=True):  # type: ignore[call-arg]
    """Audit Log database model."""

    id: int = Field(default=None, primary_key=True)
    table_name: str = Field(max_length=20)
    operation: str = Field(min_length=6, max_length=6)
    changed_at: datetime = Field(sa_column_kwargs={"server_default": func.now()})
    record_id: int | None = None
    old_data: dict[str, Any] | None = Field(sa_column=Column(JSON), default=None)
    new_data: dict[str, Any] | None = Field(sa_column=Column(JSON), default=None)


class Session(SQLModel, table=True):  # type: ignore[call-arg]
    """Session database model."""

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    refresh_token_hash: str = Field(min_length=64, max_length=64)
    user_agent: str
    ip_address: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = Field(default=False)

    user: User = Relationship(back_populates="sessions")
