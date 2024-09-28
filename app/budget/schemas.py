import uuid

from sqlmodel import Field, SQLModel

from models import Budget, Category, PredefinedCategory, User


class BudgetCreate(SQLModel):
    """Create Budget schema."""

    name: str = Field(max_length=255, title="Name of budget")
    balance: float = Field(ge=0, title="Current balance of budget")


class BudgetUpdate(SQLModel):
    """Update Budget schema."""

    name: str | None = None
    balance: float | None = None


class BudgetList(SQLModel):
    """List Budget schema."""

    data: list[Budget]


class PredefinedCategoryCreate(SQLModel):
    """Predefined category creation schema."""

    name: str = Field(max_length=255, title="Name of category")


class CategoryCreate(SQLModel):
    """Category creation schema."""

    name: str = Field(max_length=255, title="Name of category")
    category_restriction: float = Field(ge=0, title="Outlay restriction of category for budget")
    description: str | None = Field(max_length=255, title="Description of category for budget")
    is_income: bool = Field(title="Whether this category is income or outlay")


class CategoryUpdate(SQLModel):
    """Update category schema."""

    name: str | None = None
    category_restriction: float | None = None
    description: str | None = None
    is_income: bool | None = None


class PredefinedCategoryList(SQLModel):
    """List Predefined Categories schema."""

    data: list[PredefinedCategory]
    count: int


class BudgetDetails(BudgetCreate):
    """Detailed Budget schema."""

    id: uuid.UUID
    users: list[User] = []
    categories: list[Category] = []


class TransactionCreate(SQLModel):
    """Transaction input schema."""

    amount: float = Field(ge=0)
