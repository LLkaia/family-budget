import uuid

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    full_name: str = Field(max_length=255, title="Full user name")
    email: EmailStr = Field(unique=True, max_length=255, index=True, title="Email address")


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40, title="User password")


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid1, primary_key=True)
    hashed_password: str = Field()  # length of hash + salt pass
    telegram_id: int | None = Field(default=None)
    is_superuser: bool = Field(default=False)


class UserPublic(UserBase):
    id: uuid.UUID
