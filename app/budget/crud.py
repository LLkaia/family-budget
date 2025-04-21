from datetime import date
from typing import cast

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import func, or_, select
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
    TransactionList,
    TransactionUpdate,
)
from exceptions import ItemNotExistsException, ParameterMissingException
from models import Budget, Category, PredefinedCategory, Transaction, User, UserBudgetLink
from utils import PeriodFrom


async def create_budget_with_user(session: AsyncSession, budget_data: BudgetCreate, user: User) -> Budget:
    """Create a new Budget with User."""
    budget = Budget.model_validate(budget_data, update={"users": [user]})
    session.add(budget)
    await session.flush()
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
    await session.flush()
    await session.refresh(category)
    return category


async def create_predefined_category(session: AsyncSession, category: PredefinedCategoryCreate) -> PredefinedCategory:
    """Create a new predefined category."""
    predefined_category = PredefinedCategory.model_validate(category)
    session.add(predefined_category)
    await session.flush()
    await session.refresh(predefined_category)
    return cast(PredefinedCategory, predefined_category)


async def get_predefined_categories(session: AsyncSession, offset: int = 0, limit: int = 100) -> PredefinedCategoryList:
    """Retrieve Predefined Categories."""
    count = await session.exec(select(func.count()).select_from(PredefinedCategory))
    categories = await session.exec(select(PredefinedCategory).offset(offset).limit(limit))
    return PredefinedCategoryList(count=count.one(), data=categories.all())


async def remove_predefined_category(session: AsyncSession, category_id: int) -> None:
    """Remove Predefined Category."""
    category = await session.exec(select(PredefinedCategory).where(PredefinedCategory.id == category_id))
    category = category.one_or_none()
    if not category:
        raise ItemNotExistsException
    await session.delete(category)


async def get_budget_by_id_with_current_user(
    budget_id: int, session: AsyncSession, user: User, detailed: bool = False
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


async def remove_category(session: AsyncSession, category: Category) -> None:
    """Remove category from budget."""
    await session.delete(category)


async def update_category(session: AsyncSession, category: Category, new_data: CategoryUpdate) -> Category:
    """Update category with new data."""
    category.sqlmodel_update(new_data.model_dump(exclude_unset=True))
    session.add(category)
    await session.flush()
    await session.refresh(category)
    return category


async def add_user_to_budget(session: AsyncSession, budget: Budget, user: User) -> Budget:
    """Add user to existed budget."""
    budget.users.append(user)
    session.add(budget)
    await session.flush()
    await session.refresh(budget)
    return budget


async def remove_user_from_budget(session: AsyncSession, budget: Budget, user: User) -> Budget:
    """Remove user from existed budget."""
    budget.users.remove(user)
    session.add(budget)
    await session.flush()
    await session.refresh(budget)
    return budget


async def update_budget(session: AsyncSession, budget: Budget, new_data: BudgetUpdate) -> Budget:
    """Update budget with new data."""
    budget.sqlmodel_update(new_data.model_dump(exclude_unset=True))
    session.add(budget)
    await session.flush()
    await session.refresh(budget)
    return budget


async def perform_transaction_per_category(
    session: AsyncSession, budget: Budget, category: Category, transaction_data: TransactionCreate
) -> Budget:
    """Perform transaction per budget per category."""
    transaction = Transaction.model_validate(transaction_data, update={"category_id": category.id})
    budget.balance += transaction.amount if category.is_income else -transaction.amount
    session.add_all([transaction, budget])
    await session.flush()
    await session.refresh(budget)
    return budget


async def get_category_by_id_with_user(session: AsyncSession, user: User, category_id: int) -> Category | None:
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
    budget_id: int,
    user_id: int,
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
    :return: list of categories
    """
    query = select(Category)

    # aggregate with amount of transactions per category and filter by start date
    if get_transactions:
        if period_from is None:
            raise ParameterMissingException("'period_from' is required to get aggregated transactions amount.")
        date_start = period_from.get_date_start()
        query = (
            select(
                Category,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .outerjoin(Transaction)
            .where(or_(Transaction.date_performed.is_(None), Transaction.date_performed >= date_start))  # type: ignore[attr-defined]
            .group_by(Category.id)
        )

    # get related budget to check if user has access to category
    query = (
        query.join(Budget).join(UserBudgetLink).where(Budget.id == budget_id).where(UserBudgetLink.user_id == user_id)
    )

    # filter by type of category
    if is_income is not None:
        query = query.where(Category.is_income == is_income)

    categories = await session.exec(query)
    return (
        [
            CategoryWithAmount(**category.model_dump(), total_amount=total_amount or 0)
            for category, total_amount in categories
        ]
        if get_transactions
        else cast(list[CategoryWithAmount], categories.all())
    )


async def get_transaction_by_id_with_user(session: AsyncSession, user: User, transaction_id: int) -> Transaction | None:
    """Get transaction by ID."""
    transaction = await session.exec(
        select(Transaction)
        .join(Category)
        .join(Budget)
        .join(UserBudgetLink)
        .where(Transaction.id == transaction_id)
        .where(UserBudgetLink.user_id == user.id)
        .options(joinedload(Transaction.category).joinedload(Category.budget))
    )
    return cast(Transaction | None, transaction.one_or_none())


async def remove_transaction(session: AsyncSession, transaction: Transaction) -> None:
    """Remove Transaction."""
    category = transaction.category
    budget = category.budget

    budget.balance += transaction.amount if not category.is_income else -transaction.amount
    session.add(budget)
    await session.delete(transaction)


async def get_list_transactions(
    session: AsyncSession,
    budget_id: int,
    user_id: int,
    date_start: date | None,
    date_end: date | None,
    category_name_filter: str | None,
    offset: int,
    limit: int,
) -> TransactionList:
    """Get transactions.

    Validate if user has access to transaction, filter
    by date and category name prefix if specified.
    :param budget_id: budget ID.
    :param user_id: User ID
    :param session: sql session
    :param date_start: start date to filter transactions.
    :param date_end: end date to filter transactions.
    :param category_name_filter: name prefix of category.
    :param offset: offset of pagination.
    :param limit: limit of pagination.
    :return: list of transactions with total count.
    """
    query = (
        select(Transaction)
        .join(Category)
        .join(Budget)
        .join(UserBudgetLink)
        .where(Budget.id == budget_id)
        .where(UserBudgetLink.user_id == user_id)
    )
    if date_start:
        query = query.where(Transaction.date_performed >= date_start)
    if date_end:
        query = query.where(Transaction.date_performed <= date_end)
    if category_name_filter:
        query = query.where(Category.name.startswith(category_name_filter.capitalize()))

    transactions = await session.exec(query.offset(offset).limit(limit))
    count = await session.exec(select(func.count()).select_from(query.subquery()))
    return TransactionList(count=count.one(), data=transactions.all())


async def update_transaction(
    session: AsyncSession, transaction: Transaction, new_data: TransactionUpdate
) -> Transaction:
    """Update transaction with new data."""
    if new_data.amount is not None:
        difference = new_data.amount - transaction.amount
        if difference:
            category = transaction.category
            budget = category.budget
            budget.balance += difference if category.is_income else -difference
            if budget.balance < 0:
                raise ValueError("Not enough money.")
            session.add(budget)

    transaction.sqlmodel_update(new_data.model_dump(exclude_unset=True))
    session.add(transaction)

    await session.flush()
    await session.refresh(transaction)
    return transaction
