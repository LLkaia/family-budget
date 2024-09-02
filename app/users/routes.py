from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from exceptions import CredentialsException
from users.auth import authenticate_user, create_access_token, current_superuser, current_user, destroy_token
from users.crud import create_user, get_user_by_email, get_users
from users.models import Message, Token, User, UserCreate, UserPublic, UsersPublic


router = APIRouter()


@router.post("/users", response_model=UsersPublic, dependencies=[Depends(current_superuser)])
async def get_list_of_users(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> UsersPublic:
    """Get list of existed users."""
    users = await get_users(session, offset, limit)
    return users


@router.post("/login", response_model=Token)
async def login_for_access_token(
    session: Annotated[AsyncSession, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """Authenticate user with provided credentials."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise CredentialsException(
            detail="Incorrect email or password",
        )
    access_token = create_access_token(user)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", response_model=Message, dependencies=[Depends(destroy_token)])
async def logout_and_destroy_token() -> Message:
    """Logout user."""
    return Message(message="Successfully logged out.")


@router.post("/register", response_model=Message)
async def register_new_user(session: Annotated[AsyncSession, Depends(get_db)], user: UserCreate) -> Message:
    """Register new user."""
    if await get_user_by_email(session, user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
    user = await create_user(session, user)
    return Message(message=f"User '{user.full_name}' successfully registered.")


@router.post("/verify-token", response_model=UserPublic)
def test_token(user: Annotated[User, Depends(current_user)]) -> UserPublic:
    """Verify user token."""
    return user
