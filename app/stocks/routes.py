from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db
from models import StockAccount, StockPosition, User
from stocks.crud import (
    close_stock_positions_with_transactions,
    create_stock_account_with_user,
    get_active_stock_positions_per_account,
    get_stock_account_with_user_by_account_id,
    get_stock_symbols,
    open_stock_position_with_transaction,
    retrieve_stock_accounts_by_user,
    update_stock_symbols,
)
from stocks.schemas import (
    StockAccountCreate,
    StockPositionClose,
    StockPositionOpen,
    StockPositionWithCurrentPrice,
    StockSymbolList,
)
from users.auth import current_superuser, current_user
from users.schemas import Message


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
    stock_account = await get_stock_account_with_user_by_account_id(account_id, session, user)
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
    stock_account = await get_stock_account_with_user_by_account_id(account_id, session, user)
    if stock_account:
        return await open_stock_position_with_transaction(session, stock_account, stock_position)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock Account not found.")


@router.get("/account/{account_id}/stocks")
async def get_stock_positions(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    account_id: Annotated[int, Path(title="Stock Account ID")],
    get_current_price: Annotated[
        bool, Query(title="Request stock near real-time price", alias="get-current-price")
    ] = False,
) -> list[StockPosition | StockPositionWithCurrentPrice]:
    """Get all stock positions for account."""
    return await get_active_stock_positions_per_account(session, account_id, user, get_current_price)


@router.post("/account/{account_id}/stocks/close-positions")
async def close_stock_positions_by_ticket_name(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    account_id: Annotated[int, Path(title="Stock Account ID")],
    stock_position: StockPositionClose,
) -> Message:
    """Close stock positions."""
    stock_account = await get_stock_account_with_user_by_account_id(account_id, session, user)
    if stock_account:
        await close_stock_positions_with_transactions(session, stock_account, stock_position)
        return Message(message="Stock positions successfully closed.")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock Account not found.")


@router.post("/symbols/update", dependencies=[Depends(current_superuser)])
async def update_stock_symbols_task(
    session: Annotated[AsyncSession, Depends(get_db)], exchange_code: str = "US"
) -> Message:
    """Update stock symbols in table."""
    await update_stock_symbols(session, exchange_code)
    return Message(message="Stock symbols are updated.")


@router.get("/symbols", dependencies=[Depends(current_user)])
async def get_list_of_stock_symbols(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> StockSymbolList:
    """Get list of existed users."""
    return await get_stock_symbols(session, offset, limit)
