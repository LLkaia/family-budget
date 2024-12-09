from typing import cast

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import StockAccount, User
from stocks.schemas import StockAccountCreate


async def create_stock_account_with_user(
    session: AsyncSession, stock_account_data: StockAccountCreate, user: User
) -> StockAccount:
    """Create a new stock account with given user."""
    stock_account = StockAccount.model_validate(stock_account_data, update={"owner": user})
    session.add(stock_account)
    await session.commit()
    await session.refresh(stock_account)
    return cast(StockAccount, stock_account)


async def retrieve_stock_accounts_by_user(session: AsyncSession, user: User) -> list[StockAccount]:
    """Get stock accounts by user."""
    stocks_accounts = await session.exec(select(StockAccount).where(StockAccount.owner_id == user.id))
    return list(stocks_accounts.all())
