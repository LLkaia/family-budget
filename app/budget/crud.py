import uuid
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
    PredefinedCategoryCreate,
    PredefinedCategoryList,
    TransactionCreate,
)
from core.database import get_db
from exceptions import ItemNotExistsException
from models import Budget, Category, PredefinedCategory, Transaction, User
from users.auth import current_user


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
