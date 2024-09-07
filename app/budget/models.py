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
        back_populates="budgets",
        link_model=UserBudgetLink,
        cascade_delete=True,
    )
    category_links: list["BudgetCategoryLink"] = Relationship(back_populates="budget", cascade_delete=True)


class CategoryBase(SQLModel):
    """Base class for Category."""

    name: str = Field(max_length=255, title="Name of category")


class Category(CategoryBase, table=True):  # type: ignore[call-arg]
    """Category database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)

    budget_links: list["BudgetCategoryLink"] = Relationship(back_populates="category", cascade_delete=True)


class BudgetCategoryLink(SQLModel, table=True):  # type: ignore[call-arg]
    """Link table for Budget and category."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    budget_id: uuid.UUID = Field(foreign_key="budget.id", ondelete="CASCADE")
    category_id: uuid.UUID = Field(foreign_key="category.id", ondelete="CASCADE")
    category_restriction: float = Field(ge=0, title="Outlay restriction of category for budget")
    description: str | None = Field(max_length=255, title="Description of category for budget")
    is_income: bool = Field(title="Whether this category is income or outlay")

    budget: Budget = Relationship(back_populates="category_links")
    category: Category = Relationship(back_populates="budget_links")
    transactions: list["Transaction"] = Relationship(back_populates="budget_category_link", cascade_delete=True)


class Transaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Transaction database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    date: datetime = Field(default_factory=datetime.now)
    money: float = Field(ge=0, description="Amount of money income/outlay")
    budget_category_id: uuid.UUID = Field(foreign_key="budgetcategorylink.id", ondelete="CASCADE")

    budget_category_link: BudgetCategoryLink = Relationship(back_populates="transactions")
