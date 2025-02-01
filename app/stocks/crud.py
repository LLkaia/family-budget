from typing import cast

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from exceptions import ParameterMissingException
from models import AccountTransaction, StockAccount, StockPosition, User
from stocks.finnhub import get_stock_price_now
from stocks.schemas import (
    AccountTransactionData,
    AccountTransactionType,
    StockAccountCreate,
    StockPositionOpen,
    StockPositionWithCurrentPrice,
)


async def create_stock_account_with_user(
    session: AsyncSession, stock_account_data: StockAccountCreate, user: User
) -> StockAccount:
    """Create a new stock account with given user."""
    stock_account = StockAccount.model_validate(stock_account_data, update={"owner_id": user.id})
    session.add(stock_account)
    await session.commit()
    await session.refresh(stock_account)
    return cast(StockAccount, stock_account)


async def retrieve_stock_accounts_by_user(session: AsyncSession, user: User) -> list[StockAccount]:
    """Get stock accounts by user."""
    stocks_accounts = await session.exec(select(StockAccount).where(StockAccount.owner_id == user.id))
    return list(stocks_accounts.all())


async def get_stock_account_by_id_with_user(
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
        ticket_name=stock_position_data.ticket_name,
        count_active=stock_position_data.count,
        date_opened=stock_position_data.date_opened,
        price_per_stock_in=stock_position_data.price_per_stock,
        account_id=stock_account.id,
    )
    session.add(stock_position)
    await session.commit()
    await session.refresh(stock_position)

    transaction = AccountTransactionData(
        date_performed=stock_position.date_opened,
        account_id=stock_account.id,
        total_amount=stock_position.price_per_stock_in * stock_position.count_active,
        transaction_type=AccountTransactionType.STOCK_IN,
        price_per_item=stock_position.price_per_stock_in,
        count_items=stock_position.count_active,
        paid_fee=stock_position_data.paid_fee,
        ticket_name=stock_position.ticket_name,
        stock_position_id=stock_position.id,
    )
    await perform_account_transaction(session=session, account=stock_account, transaction=transaction)

    return stock_position


async def perform_account_transaction(
    session: AsyncSession, account: StockAccount, transaction: AccountTransactionData
) -> None:
    """Perform account transaction."""
    match transaction.transaction_type:
        case AccountTransactionType.STOCK_IN | AccountTransactionType.WITHDRAWAL:
            account.balance -= transaction.total_amount + transaction.paid_fee
        case AccountTransactionType.STOCK_OUT | AccountTransactionType.DIVIDENDS | AccountTransactionType.DEPOSIT:
            account.balance += transaction.total_amount - transaction.paid_fee

    if transaction.transaction_type in {AccountTransactionType.STOCK_IN, AccountTransactionType.STOCK_OUT}:
        if not (transaction.stock_position_id and transaction.ticket_name):
            raise ParameterMissingException("Missing stock position ID or ticket name.")

    if transaction.transaction_type == AccountTransactionType.DIVIDENDS and not transaction.ticket_name:
        raise ParameterMissingException("Missing ticket name.")

    if account.balance < 0:
        raise ValueError("Not enough money.")

    transaction = AccountTransaction.model_validate(transaction)
    session.add_all([transaction, account])
    await session.commit()


async def get_active_stock_positions_per_account(
    session: AsyncSession, account_id: int, user: User, current_price: bool
) -> list[StockPosition | StockPositionWithCurrentPrice]:
    """Get active stock positions per account."""
    stock_positions = await session.exec(
        select(StockPosition)
        .join(StockAccount)
        .where(StockAccount.owner_id == user.id)
        .where(StockPosition.account_id == account_id)
        .where(StockPosition.count_active > 0)
    )
    return (
        [
            StockPositionWithCurrentPrice.model_validate(
                stock_position, update={"current_price": await get_stock_price_now(stock_position.ticket_name)}
            )
            for stock_position in stock_positions
        ]
        if current_price
        else list(stock_positions.all())
    )
