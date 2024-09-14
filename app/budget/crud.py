import uuid
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Path
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from budget.models import Budget, BudgetBase, CategoryBase, PredefinedCategories, PredefinedCategory
from core.database import get_db
from users.auth import current_user
from users.models import User


async def create_budget_with_user(session: AsyncSession, budget_data: BudgetBase, user: User) -> Budget:
    """Create a new Budget with User."""
    budget = Budget.model_validate(budget_data, update={"users": [user]})
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return cast(Budget, budget)


async def create_predefined_category(session: AsyncSession, category: CategoryBase) -> PredefinedCategory:
    """Create a new predefined category."""
    predefined_category = PredefinedCategory.model_validate(category)
    session.add(predefined_category)
    await session.commit()
    await session.refresh(predefined_category)
    return cast(PredefinedCategory, predefined_category)


async def get_predefined_categories(session: AsyncSession, offset: int = 0, limit: int = 100) -> PredefinedCategories:
    """Retrieve Predefined Categories."""
    count = await session.exec(select(func.count()).select_from(PredefinedCategory))
    categories = await session.exec(select(PredefinedCategory).offset(offset).limit(limit))
    return PredefinedCategories(count=count.one(), data=categories.all())


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
        if is_user_belongs_to_budget or user.is_superuser:
            return cast(Budget, budget)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")
