import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from budget.models import Budget, BudgetBase, Category, UserBudgetLink


class UserBase(SQLModel):
    """Base class for User."""

    full_name: str = Field(max_length=255, title="Full user name")
    email: EmailStr = Field(unique=True, max_length=255, index=True, title="Email address")


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(min_length=8, max_length=40, title="User password")


class User(UserBase, table=True):  # type: ignore[call-arg]
    """User database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    hashed_password: str = Field(min_length=59, max_length=60)
    telegram_id: int | None = Field(default=None)
    is_superuser: bool = Field(default=False)

    budgets: list[Budget] = Relationship(back_populates="users", link_model=UserBudgetLink)


class UserPublic(UserBase):
    """Public User model."""

    id: uuid.UUID


class UserDetails(UserPublic):
    """Detailed User response model."""

    telegram_id: int | None
    is_superuser: bool
    budgets: list[Budget] = []


class UsersPublic(SQLModel):
    """Many Users response model."""

    data: list[UserPublic]
    count: int


class BudgetDetails(BudgetBase):
    """Detailed Budget response model."""

    id: uuid.UUID
    users: list[User] = []
    categories: list[Category] = []


class Token(SQLModel):
    """JWT Token model."""

    access_token: str
    token_type: str


class TokenPayload(SQLModel):
    """JWT Token payload."""

    sub: EmailStr
    exp: datetime
    jti: uuid.UUID


class Message(SQLModel):
    """Standard response model."""

    message: str
