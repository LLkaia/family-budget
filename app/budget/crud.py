import uuid
from datetime import date
from typing import cast

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

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
from exceptions import ItemNotExistsException, ParameterMissingException
from models import Budget, Category, PredefinedCategory, Transaction, User, UserBudgetLink
from utils import PeriodFrom


async def create_budget_with_user(session: AsyncSession, budget_data: BudgetCreate, user: User) -> Budget:
    """Create a new Budget with User."""
    budget = Budget.model_validate(budget_data, update={"users": [user]})
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return cast(Budget, budget)


async def retrieve_budgets_by_user(session: AsyncSession, user: User) -> list[Budget]:
    """Retrieve Budgets with User."""
    budgets = await session.exec(select(Budget).where(Budget.users.any(id=user.id)))  # type: ignore[attr-defined]
    return list(budgets.all())


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
    budget_id: uuid.UUID, session: AsyncSession, user: User, detailed: bool = False
) -> Budget | None:
    """Get Budget by ID for member."""
    query = select(Budget).where(Budget.id == budget_id, Budget.users.any(id=user.id))  # type: ignore[attr-defined]
    if detailed:
        query = query.options(selectinload(Budget.users), joinedload(Budget.categories))
    budget = await session.exec(query)
    return cast(Budget | None, budget.unique().one_or_none())


async def remove_budget(session: AsyncSession, budget: Budget) -> None:
    """Remove existed budget."""
    await session.delete(budget)
    await session.commit()


async def remove_category(session: AsyncSession, category: Category) -> None:
    """Remove category from budget."""
    await session.delete(category)
    await session.commit()


async def update_category(session: AsyncSession, category: Category, new_data: CategoryUpdate) -> Category:
    """Update category with new data."""
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


async def perform_transaction_per_category(
    session: AsyncSession, budget: Budget, category: Category, transaction_data: TransactionCreate
) -> Budget:
    """Perform transaction per budget per category."""
    transaction = Transaction.model_validate(transaction_data, update={"category_id": category.id})
    budget.balance += transaction.amount if category.is_income else -transaction.amount
    session.add_all([transaction, budget])
    await session.commit()
    await session.refresh(budget)
    return budget


async def get_category_by_id_with_user(session: AsyncSession, user: User, category_id: uuid.UUID) -> Category | None:
    """Get category from budget by ID."""
    category = await session.exec(
        select(Category)
        .join(Budget)
        .join(UserBudgetLink)
        .where(Category.id == category_id)
        .where(UserBudgetLink.user_id == user.id)
    )
    return cast(Category | None, category.one_or_none())


async def get_categories_by_budget_and_user(
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    is_income: bool | None,
    get_transactions: bool | None,
    period_from: PeriodFrom | None,
) -> list[CategoryWithAmount]:
    """Get categories for budget.

    Validate if user has access to budget, filter
    by type, and get amount of transactions per
    period per category.
    :param budget_id: budget ID.
    :param user_id: User ID
    :param session: sql session
    :param is_income: whether categories are income
        or outlay.
    :param get_transactions: whether to fetch amount
        of transactions per category per period.
    :param period_from: period for amount aggregation
    :return:
    """
    # get categories for budget, if user belongs to budget
    query = (
        select(Category)
        .join(Budget)
        .join(UserBudgetLink)
        .where(Budget.id == budget_id)
        .where(UserBudgetLink.user_id == user_id)
    )
    # filter by type
    if is_income is not None:
        query = query.where(Category.is_income == is_income)

    categories = await session.exec(query)

    # calculate amount of transaction per category
    if get_transactions:
        if period_from is None:
            raise ParameterMissingException("'period_from' is required to get aggregated transactions amount.")
        date_start = period_from.get_date_start()
        categories_with_amount = []
        for category in categories:
            categories_with_amount.append(
                CategoryWithAmount.model_validate(
                    category.model_dump(),
                    update={"total_amount": await retrieve_amount_per_category(session, category.id, date_start)},
                )
            )
        return categories_with_amount

    return cast(list[CategoryWithAmount], categories.all())


async def retrieve_amount_per_category(
    session: AsyncSession,
    category_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
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
        query = query.where(Transaction.date_performed >= start_date)
    if end_date:
        query = query.where(Transaction.date_performed <= end_date)
    result = await session.exec(query)
    return result.one_or_none() or 0.0
