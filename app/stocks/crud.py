from datetime import date
from typing import cast

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from exceptions import ParameterMissingException
from models import AccountTransaction, StockAccount, StockPosition, User
from stocks.schemas import AccountTransactionType, StockAccountCreate, StockPositionOpen, StockPositionWithCurrentPrice
from utils import get_stock_price_now


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

    await perform_account_transaction(
        session=session,
        transaction_type=AccountTransactionType.STOCK_IN,
        account=stock_account,
        date_performed=stock_position.date_opened,
        price_per_item=stock_position.price_per_stock_in,
        count_items=stock_position.count_active,
        paid_fee=stock_position_data.paid_fee,
        stock_position_id=stock_position.id,
        ticket_name=stock_position.ticket_name,
    )

    return stock_position


async def perform_account_transaction(
    session: AsyncSession,
    transaction_type: AccountTransactionType,
    account: StockAccount,
    date_performed: date,
    price_per_item: float,
    count_items: int = 1,
    paid_fee: float = 0,
    taxes_to_pay: float = 0,
    stock_position_id: int | None = None,
    ticket_name: str | None = None,
) -> None:
    """Perform account transaction."""
    total_amount = price_per_item * count_items

    match transaction_type:
        # spend account money
        case AccountTransactionType.STOCK_IN if stock_position_id and ticket_name:
            account.balance -= total_amount + paid_fee
        case AccountTransactionType.WITHDRAWAL:
            account.balance -= total_amount + paid_fee

        # deposit money into the account
        case AccountTransactionType.STOCK_OUT if stock_position_id and ticket_name:
            account.balance += total_amount - paid_fee
        case AccountTransactionType.DIVIDENDS if ticket_name:
            account.balance += total_amount - paid_fee
        case AccountTransactionType.DEPOSIT:
            account.balance += total_amount - paid_fee

        case _:
            raise ParameterMissingException("Not all parameters were provided to perform account transaction.")

    if account.balance < 0:
        raise ValueError("Not enough money.")

    transaction = AccountTransaction(
        transaction_type=transaction_type,
        date_performed=date_performed,
        account_id=account.id,
        price_per_item=price_per_item,
        count_items=count_items,
        paid_fee=paid_fee,
        taxes_to_pay=taxes_to_pay,
        ticket_name=ticket_name,
        stock_position_id=stock_position_id,
        total_amount=total_amount,
    )
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
