import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class UserBudgetLink(SQLModel, table=True):  # type: ignore[call-arg]
    """Link table for User and Budget."""

    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    budget_id: uuid.UUID = Field(foreign_key="budget.id", primary_key=True, ondelete="CASCADE")


class BudgetBase(SQLModel):
    """Base class for Budget."""

    name: str = Field(max_length=255, title="Name of budget")
    balance: float = Field(ge=0, title="Current balance of budget")


class Budget(BudgetBase, table=True):  # type: ignore[call-arg]
    """Budget database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)

    users: list["User"] = Relationship(  # type: ignore[name-defined] # noqa: F821
        back_populates="budgets", link_model=UserBudgetLink
    )
    categories: list["Category"] = Relationship(back_populates="budget", cascade_delete=True)


class CategoryBase(SQLModel):
    """Base class for Category."""

    name: str = Field(max_length=255, title="Name of category")


class Category(CategoryBase, table=True):  # type: ignore[call-arg]
    """Category database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    category_restriction: float = Field(ge=0, title="Outlay restriction of category for budget")
    description: str | None = Field(max_length=255, title="Description of category for budget")
    is_income: bool = Field(title="Whether this category is income or outlay")
    budget_id: uuid.UUID = Field(foreign_key="budget.id", ondelete="CASCADE")

    budget: Budget = Relationship(back_populates="categories")
    transactions: list["Transaction"] = Relationship(back_populates="categories", cascade_delete=True)


class PredefinedCategory(CategoryBase, table=True):  # type: ignore[call-arg]
    """Predefined categories database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)


class PredefinedCategories(SQLModel):
    """Many Predefined Categories response model."""

    data: list[PredefinedCategory]
    count: int


class Transaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Transaction database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    date: datetime = Field(default_factory=datetime.now)
    money: float = Field(ge=0, description="Amount of money income/outlay")
    category_id: uuid.UUID = Field(foreign_key="category.id", ondelete="CASCADE")

    categories: Category = Relationship(back_populates="transactions")
