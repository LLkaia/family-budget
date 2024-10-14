import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    """Base class for User schema."""

    email: EmailStr = Field(unique=True, max_length=255, index=True, title="Email address")


class UserCreate(UserBase):
    """User creation schema."""

    full_name: str = Field(max_length=255, title="Full user name")
    password: str = Field(min_length=8, max_length=40, title="User password")


class UserPublic(UserBase):
    """Public User schema."""

    full_name: str = Field(max_length=255, title="Full user name")
    id: uuid.UUID


class UserDetails(UserPublic):
    """Detailed User schema."""

    telegram_id: int | None
    is_superuser: bool


class UserList(SQLModel):
    """List Users schema."""

    data: list[UserPublic]
    count: int


class Token(SQLModel):
    """JWT Token schema."""

    access_token: str
    token_type: str


class TokenPayload(SQLModel):
    """JWT Token payload schema."""

    sub: EmailStr
    exp: datetime
    jti: uuid.UUID


class Message(SQLModel):
    """Standard response schema."""

    message: str
