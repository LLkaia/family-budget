from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from models import StockAccount, User
from stocks.crud import create_stock_account_with_user, retrieve_stock_accounts_by_user
from stocks.schemas import StockAccountCreate
from users.auth import current_user


router = APIRouter()


@router.post("/account", status_code=status.HTTP_201_CREATED)
async def create_stock_account(
    stock_account: StockAccountCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> StockAccount:
    """Create a stock account."""
    return await create_stock_account_with_user(session, stock_account, user)


@router.get("/account")
async def get_my_stock_accounts(
    user: Annotated[User, Depends(current_user)], session: Annotated[AsyncSession, Depends(get_db)]
) -> list[StockAccount]:
    """Get all stock accounts."""
    return await retrieve_stock_accounts_by_user(session, user)
