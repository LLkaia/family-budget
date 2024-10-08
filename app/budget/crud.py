import uuid
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Path
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from budget.schemas import (
    BudgetCreate,
    BudgetUpdate,
    CategoryCreate,
    CategoryUpdate,
    CategoryWithAmount,
    PredefinedCategoryCreate,
    PredefinedCategoryList,
    TransactionCreate,
)
from core.database import get_db
from exceptions import ItemNotExistsException, ParameterMissingException
from models import Budget, Category, PredefinedCategory, Transaction, User
from users.auth import current_user
from utils import PeriodFrom, get_datatime_now


async def create_budget_with_user(session: AsyncSession, budget_data: BudgetCreate, user: User) -> Budget:
    """Create a new Budget with User."""
    budget = Budget.model_validate(budget_data, update={"users": [user]})
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return cast(Budget, budget)


async def create_category_and_add_to_budget(
    session: AsyncSession, budget: Budget, category: CategoryCreate
) -> Category:
    """Create a new category and add it to the budget."""
    category = Category.model_validate(category, update={"budget_id": budget.id})
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def create_predefined_category(session: AsyncSession, category: PredefinedCategoryCreate) -> PredefinedCategory:
    """Create a new predefined category."""
    predefined_category = PredefinedCategory.model_validate(category)
    session.add(predefined_category)
    await session.commit()
    await session.refresh(predefined_category)
    return cast(PredefinedCategory, predefined_category)


async def get_predefined_categories(session: AsyncSession, offset: int = 0, limit: int = 100) -> PredefinedCategoryList:
    """Retrieve Predefined Categories."""
    count = await session.exec(select(func.count()).select_from(PredefinedCategory))
    categories = await session.exec(select(PredefinedCategory).offset(offset).limit(limit))
    return PredefinedCategoryList(count=count.one(), data=categories.all())


async def remove_predefined_category(session: AsyncSession, category_id: uuid.UUID) -> None:
    """Remove Predefined Category."""
    category = await session.exec(select(PredefinedCategory).where(PredefinedCategory.id == category_id))
    category = category.one_or_none()
    if not category:
        raise ItemNotExistsException
    await session.delete(category)
    await session.commit()


async def get_budget_by_id_with_current_user(
    budget_id: Annotated[uuid.UUID, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Budget:
    """Get Budget by ID for member or admin user."""
    budget = await session.exec(select(Budget).where(Budget.id == budget_id))
    budget = budget.unique().one_or_none()
    if budget:
        is_user_belongs_to_budget = any(user.id == budget_user.id for budget_user in budget.users)
        if is_user_belongs_to_budget or user.is_superuser:  # TODO: remove access to budget for admin
            return cast(Budget, budget)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")


async def remove_budget(session: AsyncSession, budget: Budget) -> None:
    """Remove existed budget."""
    await session.delete(budget)
    await session.commit()


async def remove_category_from_budget(session: AsyncSession, budget: Budget, category_id: uuid.UUID) -> None:
    """Remove category from budget."""
    category = get_category_by_id_from_existed_budget(budget, category_id)
    await session.delete(category)
    await session.commit()


async def update_category(
    session: AsyncSession, budget: Budget, category_id: uuid.UUID, new_data: CategoryUpdate
) -> Category:
    """Update category with new data."""
    category = get_category_by_id_from_existed_budget(budget, category_id)
    category.sqlmodel_update(new_data.model_dump(exclude_unset=True))
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def add_user_to_budget(session: AsyncSession, budget: Budget, user: User) -> Budget:
    """Add user to existed budget."""
    budget.users.append(user)
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return budget


async def remove_user_from_budget(session: AsyncSession, budget: Budget, user: User) -> Budget:
    """Remove user from existed budget."""
    budget.users.remove(user)
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return budget


async def update_budget(session: AsyncSession, budget: Budget, new_data: BudgetUpdate) -> Budget:
    """Update budget with new data."""
    budget.sqlmodel_update(new_data.model_dump(exclude_unset=True))
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return budget


async def perform_transaction_per_budget(
    session: AsyncSession, budget: Budget, category_id: uuid.UUID, transaction_data: TransactionCreate
) -> Budget:
    """Perform transaction per budget per category."""
    category = get_category_by_id_from_existed_budget(budget, category_id)
    transaction = Transaction.model_validate(transaction_data, update={"category_id": category.id})
    budget.balance += transaction.amount if category.is_income else -transaction.amount
    session.add_all([transaction, budget])
    await session.commit()
    await session.refresh(budget)
    return budget


def get_category_by_id_from_existed_budget(budget: Budget, category_id: uuid.UUID) -> Category:
    """Get category from budget by ID."""
    category = next((cat for cat in budget.categories if cat.id == category_id), None)
    if not category:
        raise ItemNotExistsException
    return category


async def filter_categories(
    session: AsyncSession,
    categories: list[Category],
    is_income: bool,
    get_transactions: bool,
    period_from: PeriodFrom | None,
) -> list[CategoryWithAmount]:
    """Filter categories by income and period.

    :param session: DB session
    :param categories: Categories to filter
    :param is_income: whether income or not
    :param get_transactions: whether retrieve amount
        of transaction per period.
    :param period_from: period for amount of transactions,
        is required if param get_transactions is True.
    :return: list of filtered Categories
    """
    result = []
    for category in categories:
        if category.is_income == is_income:
            filtered_category = CategoryWithAmount(**category.model_dump())

            # aggregate related transactions per period
            if get_transactions:
                if period_from is None:
                    raise ParameterMissingException("'period_from' is required to get aggregated transactions amount.")

                date_start = get_datatime_now().replace(**period_from.get_datatime_start())  # type: ignore[arg-type]
                filtered_category.amount = await retrieve_amount_per_category(session, category.id, date_start)

            result.append(filtered_category)
    return result


async def retrieve_amount_per_category(
    session: AsyncSession,
    category_id: uuid.UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> float:
    """Retrieve aggregated amount per category.

    :param session: DB session
    :param category_id: category ID
    :param start_date: start date to filter
    :param end_date: end date to filter
    :return: list of filtered Categories
    """
    query = select(func.sum(Transaction.amount)).where(Transaction.category_id == category_id)
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    result = await session.exec(query)
    return result.one_or_none() or 0.0
