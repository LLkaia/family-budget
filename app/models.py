import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class UserBudgetLink(SQLModel, table=True):  # type: ignore[call-arg]
    """Link table for User and Budget."""

    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    budget_id: uuid.UUID = Field(foreign_key="budget.id", primary_key=True, ondelete="CASCADE")


class Budget(SQLModel, table=True):  # type: ignore[call-arg]
    """Budget database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    name: str = Field(max_length=255)
    balance: float = Field(ge=0)

    users: list["User"] = Relationship(
        back_populates="budgets", link_model=UserBudgetLink, sa_relationship_kwargs={"lazy": "joined"}
    )
    categories: list["Category"] = Relationship(
        back_populates="budget", cascade_delete=True, sa_relationship_kwargs={"lazy": "selectin"}
    )


class User(SQLModel, table=True):  # type: ignore[call-arg]
    """User database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    full_name: str = Field(max_length=255)
    email: EmailStr = Field(unique=True, max_length=255, index=True)
    hashed_password: str = Field(min_length=59, max_length=60)
    telegram_id: int | None = Field(default=None)
    is_superuser: bool = Field(default=False)

    budgets: list[Budget] = Relationship(back_populates="users", link_model=UserBudgetLink)


class Category(SQLModel, table=True):  # type: ignore[call-arg]
    """Category database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    name: str = Field(max_length=255)
    category_restriction: float = Field(ge=0)
    description: str | None = Field(max_length=255)
    is_income: bool
    budget_id: uuid.UUID = Field(foreign_key="budget.id", ondelete="CASCADE")

    budget: Budget = Relationship(back_populates="categories")
    transactions: list["Transaction"] = Relationship(back_populates="category", cascade_delete=True)

    __table_args__ = (UniqueConstraint("budget_id", "name", name="uq_budget_category"),)


class PredefinedCategory(SQLModel, table=True):  # type: ignore[call-arg]
    """Predefined categories database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    name: str = Field(max_length=255, unique=True)


class Transaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Transaction database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    date: datetime = Field(default_factory=datetime.now)
    amount: float = Field(ge=0)
    category_id: uuid.UUID = Field(foreign_key="category.id", ondelete="CASCADE")

    category: Category = Relationship(back_populates="transactions")
