from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from exceptions import CredentialsException
from models import User
from users.auth import (
    authenticate_user,
    create_access_token,
    create_new_session_for_user,
    current_superuser,
    current_user,
    destroy_tokens,
    verify_session,
)
from users.crud import create_user, get_sessions_by_user_id, get_users, revoke_user_sessions
from users.schemas import Message, SessionPublic, Token, UserCreate, UserDetails, UserList


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
async def login_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
) -> Token:
    """Authenticate user with provided credentials."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise CredentialsException

    access_token = create_access_token(user)
    await create_new_session_for_user(session, user, request, response)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", dependencies=[Depends(destroy_tokens)])
async def logout_and_destroy_tokens() -> Message:
    """Logout user."""
    return Message(message="Successfully logged out.")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_new_user(session: Annotated[AsyncSession, Depends(get_db)], user: UserCreate) -> Message:
    """Register new user."""
    try:
        user = await create_user(session, user)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
    else:
        return Message(message=f"User '{user.full_name}' successfully registered.")


@router.post("/verify", dependencies=[Depends(current_user)])
async def verify_access_token() -> Message:
    """Verify access token."""
    return Message(message="Token is valid.")


@router.post("/refresh")
async def refresh_access_token(session: Annotated[AsyncSession, Depends(get_db)], request: Request) -> Token:
    """Refresh access token."""
    user_session = await verify_session(session, request)
    access_token = create_access_token(user_session.user)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/sessions")
async def get_user_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    is_active: Annotated[bool, Query(alias="active")] = True,
) -> list[SessionPublic]:
    """Get user sessions."""
    result = await get_sessions_by_user_id(session, user.id, is_active)
    return result


@router.post("/sessions/destroy", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_user_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    session_id: Annotated[int | None, Query(alias="session")] = None,
) -> None:
    """Destroy user sessions."""
    await revoke_user_sessions(session, user, session_id)
