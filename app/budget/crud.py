from typing import cast

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from budget.models import Budget, BudgetBase, CategoryBase, PredefinedCategories, PredefinedCategory
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
