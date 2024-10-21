from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from exceptions import CredentialsException
from models import User
from users.auth import authenticate_user, create_access_token, current_superuser, current_user, destroy_token
from users.crud import create_user, get_users
from users.schemas import Message, Token, UserCreate, UserDetails, UserList


router = APIRouter()


@router.get("", response_model=UserDetails, response_model_exclude_none=True)
async def get_me_detailed(user: Annotated[User, Depends(current_user)]) -> User:
    """Get current user info."""
    return user


@router.get("/users", dependencies=[Depends(current_superuser)])
async def get_list_of_users(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> UserList:
    """Get list of existed users."""
    users = await get_users(session, offset, limit)
    return users


@router.post("/login")
async def login_for_access_token(
    session: Annotated[AsyncSession, Depends(get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """Authenticate user with provided credentials."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise CredentialsException
    access_token = create_access_token(user)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", dependencies=[Depends(destroy_token)])
async def logout_and_destroy_token() -> Message:
    """Logout user."""
    return Message(message="Successfully logged out.")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(session: Annotated[AsyncSession, Depends(get_db)], user: UserCreate) -> Message:
    """Register new user."""
    try:
        user = await create_user(session, user)
        return Message(message=f"User '{user.full_name}' successfully registered.")
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")


@router.post("/verify-token", dependencies=[Depends(current_user)])
def test_token() -> Message:
    """Verify user token."""
    return Message(message="Token is valid.")
