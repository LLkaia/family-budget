from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from models import StockAccount, StockPosition, User
from stocks.crud import (
    create_stock_account_with_user,
    get_stock_account_by_id_with_user,
    open_stock_position_with_transaction,
    retrieve_stock_accounts_by_user,
)
from stocks.schemas import StockAccountCreate, StockPositionOpen
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


@router.get("/account/{account_id}")
async def get_stock_account(
    account_id: Annotated[int, Path(title="Stock Account ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> StockAccount:
    """Get stock account by id."""
    stock_account = await get_stock_account_by_id_with_user(account_id, session, user)
    if stock_account:
        return stock_account
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock Account not found.")


@router.post("/account/{account_id}/stocks", status_code=status.HTTP_201_CREATED)
async def open_stock_position(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    account_id: Annotated[int, Path(title="Stock Account ID")],
    stock_position: StockPositionOpen,
) -> StockPosition:
    """Open stock position for account."""
    stock_account = await get_stock_account_by_id_with_user(account_id, session, user)
    if stock_account:
        return await open_stock_position_with_transaction(session, stock_account, stock_position)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock Account not found.")
