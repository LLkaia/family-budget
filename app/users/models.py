import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    """Base class for User."""

    full_name: str = Field(max_length=255, title="Full user name")
    email: EmailStr = Field(unique=True, max_length=255, index=True, title="Email address")


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(min_length=8, max_length=40, title="User password")


class User(UserBase, table=True):  # type: ignore
    """User database model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    hashed_password: str = Field(min_length=59, max_length=60)
    telegram_id: int | None = Field(default=None)
    is_superuser: bool = Field(default=False)


class UserPublic(UserBase):
    """Public User model."""

    id: uuid.UUID


class UsersPublic(SQLModel):
    """Many Users response model."""

    data: list[UserPublic]
    count: int


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
