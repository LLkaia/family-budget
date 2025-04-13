import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, EmailStr
from sqlmodel import Field, SQLModel

from validators import validate_password


class UserBase(SQLModel):
    """Base class for User schema."""

    email: EmailStr = Field(unique=True, max_length=255, index=True, title="Email address")


class UserCreate(UserBase):
    """User creation schema."""

    full_name: str = Field(max_length=255, title="Full user name")
    password: "PasswordStr" = Field(title="User password")


class UserPublic(UserBase):
    """Public User schema."""

    full_name: str = Field(max_length=255, title="Full user name")
    id: int


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


class UserFixture(UserCreate):
    """User fixture for tests."""

    id: int
    token: str | None = None

    def get_headers(self) -> dict[str, str]:
        """Return the headers with the authorization token."""
        return {"Authorization": f"Bearer {self.token}"}


class SessionPublic(SQLModel):
    """Session public schema."""

    id: int
    user_agent: str
    ip_address: str
    created_at: datetime
    is_active: bool


PasswordStr = Annotated[str, AfterValidator(validate_password)]
