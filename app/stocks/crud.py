import math
from itertools import batched
from typing import cast

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import PSQL_QUERY_ALLOWED_MAX_ARGS
from exceptions import ParameterMissingException
from models import AccountTransaction, StockAccount, StockPosition, StockSymbol, User
from stocks.dividends import get_dividend_history_by_stock_symbol
from stocks.finnhub import get_latest_stock_price, get_stock_symbols_data
from stocks.schemas import (
    AccountTransactionData,
    AccountTransactionType,
    StockAccountCreate,
    StockPositionClose,
    StockPositionOpen,
    StockPositionPublic,
    StockPositionWithCurrentPrice,
    StockSymbolList,
    StockSymbolWithDividendsHistory,
)


async def create_stock_account_with_user(
    session: AsyncSession, stock_account_data: StockAccountCreate, user: User
) -> StockAccount:
    """Create a new stock account with given user."""
    stock_account = StockAccount.model_validate(stock_account_data, update={"owner_id": user.id})
    session.add(stock_account)
    await session.flush()
    await session.refresh(stock_account)
    return cast(StockAccount, stock_account)


async def retrieve_stock_accounts_by_user(session: AsyncSession, user: User) -> list[StockAccount]:
    """Get stock accounts by user."""
    stocks_accounts = await session.exec(select(StockAccount).where(StockAccount.owner_id == user.id))
    return list(stocks_accounts.all())


async def get_stock_account_with_user_by_account_id(
    stock_account_id: int, session: AsyncSession, user: User
) -> StockAccount | None:
    """Get Stock Account by ID for owner."""
    query = select(StockAccount).where(StockAccount.id == stock_account_id, StockAccount.owner_id == user.id)
    account = await session.exec(query)
    return cast(StockAccount | None, account.unique().one_or_none())


async def open_stock_position_with_transaction(
    session: AsyncSession, stock_account: StockAccount, stock_position_data: StockPositionOpen
) -> StockPosition:
    """Open stock position with transaction."""
    stock_position = StockPosition(
        stock_symbol_id=stock_position_data.stock_symbol_id,
        count_active=stock_position_data.count,
        datetime_opened=stock_position_data.datetime_opened,
        price_per_stock_in=stock_position_data.price_per_stock,
        account_id=stock_account.id,
    )
    session.add(stock_position)
    await session.flush()
    await session.refresh(stock_position)

    transaction = AccountTransactionData(
        datetime_performed=stock_position.datetime_opened,
        account_id=stock_account.id,
        total_amount=stock_position.price_per_stock_in * stock_position.count_active,
        transaction_type=AccountTransactionType.STOCK_IN,
        price_per_item=stock_position.price_per_stock_in,
        count_items=stock_position.count_active,
        paid_fee=stock_position_data.paid_fee,
        stock_symbol_id=stock_position.stock_symbol_id,
        stock_position_id=stock_position.id,
    )
    perform_account_transaction(session=session, account=stock_account, transaction=transaction)
    return stock_position


async def close_stock_positions_with_transactions(
    session: AsyncSession, stock_account: StockAccount, stock_position_to_close: StockPositionClose
) -> None:
    """Close stock positions with transactions."""
    stock_positions = await session.exec(
        select(StockPosition)
        .where(StockPosition.account_id == stock_account.id)
        .where(StockPosition.count_active > 0)
        .where(StockPosition.stock_symbol_id == stock_position_to_close.stock_symbol_id)
        .order_by(StockPosition.datetime_opened)
    )

    total_count_to_subtract = stock_position_to_close.count
    for stock_position in stock_positions:
        subtracted_count = min(total_count_to_subtract, stock_position.count_active)
        stock_position.count_active -= subtracted_count
        total_count_to_subtract -= subtracted_count
        session.add(stock_position)

        transaction = AccountTransactionData(
            datetime_performed=stock_position_to_close.datetime_closed,
            account_id=stock_account.id,
            total_amount=stock_position_to_close.price_per_stock * subtracted_count,
            transaction_type=AccountTransactionType.STOCK_OUT,
            price_per_item=stock_position_to_close.price_per_stock,
            count_items=subtracted_count,
            paid_fee=stock_position_to_close.paid_fee,
            stock_symbol_id=stock_position_to_close.stock_symbol_id,
            stock_position_id=stock_position.id,
        )
        perform_account_transaction(session=session, account=stock_account, transaction=transaction)

        if total_count_to_subtract == 0:
            break

    if total_count_to_subtract > 0:
        raise ValueError(
            f"Cannot close stock positions: too many stocks to close. Remaining: {total_count_to_subtract}."
        )


def perform_account_transaction(
    session: AsyncSession, account: StockAccount, transaction: AccountTransactionData
) -> None:
    """Perform account transaction."""
    match transaction.transaction_type:
        case AccountTransactionType.STOCK_IN | AccountTransactionType.WITHDRAWAL:
            account.balance -= transaction.total_amount + transaction.paid_fee
        case AccountTransactionType.STOCK_OUT | AccountTransactionType.DIVIDENDS | AccountTransactionType.DEPOSIT:
            account.balance += transaction.total_amount - transaction.paid_fee

    if transaction.transaction_type in {AccountTransactionType.STOCK_IN, AccountTransactionType.STOCK_OUT}:
        if not (transaction.stock_position_id and transaction.stock_symbol_id):
            raise ParameterMissingException("Missing stock position ID or stock symbol ID.")

    if transaction.transaction_type == AccountTransactionType.DIVIDENDS and not transaction.stock_symbol_id:
        raise ParameterMissingException("Missing stock symbol ID.")

    if account.balance < 0:
        raise ValueError("Not enough money.")

    transaction = AccountTransaction.model_validate(transaction)
    session.add_all([transaction, account])


async def get_active_stock_positions_per_account(
    session: AsyncSession, account_id: int, user: User, get_current_price: bool
) -> list[StockPositionPublic | StockPositionWithCurrentPrice]:
    """Get active stock positions per account."""
    stock_positions = await session.exec(
        select(StockPosition)
        .join(StockAccount)
        .where(StockAccount.owner_id == user.id)
        .where(StockPosition.account_id == account_id)
        .where(StockPosition.count_active > 0)
        .options(joinedload(StockPosition.stock_symbol))
    )
    return (
        [
            StockPositionWithCurrentPrice.model_validate(
                stock_position,
                update={"current_price": await get_latest_stock_price(stock_position.stock_symbol.symbol)},
            )
            for stock_position in stock_positions
        ]
        if get_current_price
        else list(stock_positions.all())
    )


async def update_stock_symbols(session: AsyncSession, exchange_code: str = "US") -> None:
    """Update stock symbols table with fresh data."""
    stock_symbols_data = await get_stock_symbols_data(exchange_code)

    # allowed items depends on parameters of each item
    allowed_items_per_query = int(math.floor(PSQL_QUERY_ALLOWED_MAX_ARGS / len(stock_symbols_data[0])))

    # make generator which returns allowed amount of items per iteration
    for data in batched(stock_symbols_data, allowed_items_per_query):
        query = insert(StockSymbol).values(data)

        # if item with same figi exists -> update symbol and description
        query = query.on_conflict_do_update(
            constraint="stocksymbol_figi_key",
            set_={StockSymbol.symbol: query.excluded.symbol, StockSymbol.description: query.excluded.description},
        )

        await session.exec(query)


async def get_stock_symbols(session: AsyncSession, offset: int = 0, limit: int = 100) -> StockSymbolList:
    """Retrieve stock symbols."""
    count = await session.exec(select(func.count()).select_from(StockSymbol))
    stock_symbols = await session.exec(select(StockSymbol).order_by(StockSymbol.symbol).offset(offset).limit(limit))
    return StockSymbolList(count=count.one(), data=stock_symbols.all())


async def retrieve_stock_symbol_by_id(
    session: AsyncSession, symbol_id: int, get_div_history: bool = False
) -> StockSymbolWithDividendsHistory | None:
    """Get Info by Stock Symbol ID."""
    stock_symbol = await session.exec(select(StockSymbol).where(StockSymbol.id == symbol_id))
    stock_symbol = stock_symbol.one_or_none()

    if stock_symbol and get_div_history:
        stock_symbol = StockSymbolWithDividendsHistory.model_validate(
            stock_symbol, update={"dividends_history": await get_dividend_history_by_stock_symbol(stock_symbol.symbol)}
        )

    return cast(StockSymbolWithDividendsHistory | None, stock_symbol)
