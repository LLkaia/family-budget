from datetime import date

from sqlmodel import Field, SQLModel

from models import Category, PredefinedCategory, Transaction
from users.schemas import UserPublic
from validators import CurrencyValue


class BudgetCreate(SQLModel):
    """Create Budget schema."""

    name: str = Field(max_length=255, title="Name of budget")
    balance: CurrencyValue = Field(ge=0, title="Current balance of budget")


class BudgetUpdate(SQLModel):
    """Update Budget schema."""

    name: str | None = None
    balance: CurrencyValue | None = Field(default=None, ge=0, title="Current balance of budget")


class BudgetPublic(BudgetCreate):
    """Public Budget schema."""

    id: int


class PredefinedCategoryCreate(SQLModel):
    """Predefined category creation schema."""

    name: str = Field(max_length=255, title="Name of category")


class CategoryCreate(SQLModel):
    """Category creation schema."""

    name: str = Field(max_length=255, title="Name of category")
    category_restriction: CurrencyValue = Field(ge=0, title="Outlay restriction of category for budget")
    description: str | None = Field(max_length=255, title="Description of category for budget", default=None)
    is_income: bool = Field(title="Whether this category is income or outlay", default=False)


class CategoryWithAmount(CategoryCreate):
    """Category with calculated transactions amount."""

    id: int
    total_amount: CurrencyValue | None = Field(default=None, ge=0)


class CategoryUpdate(SQLModel):
    """Update category schema."""

    name: str | None = None
    category_restriction: CurrencyValue | None = Field(ge=0, default=None)
    description: str | None = None
    is_income: bool | None = None


class PredefinedCategoryList(SQLModel):
    """List Predefined Categories schema."""

    data: list[PredefinedCategory]
    count: int


class BudgetDetails(BudgetPublic):
    """Detailed Budget schema."""

    users: list[UserPublic] = []
    categories: list[Category] = []


class TransactionCreate(SQLModel):
    """Transaction input schema."""

    amount: CurrencyValue = Field(ge=0)
    date_performed: date


class TransactionList(SQLModel):
    """List Transactions schema."""

    data: list[Transaction]
    count: int


class TransactionUpdate(SQLModel):
    """Transaction update schema."""

    amount: CurrencyValue | None = Field(ge=0, default=None)
    date_performed: date | None = None
