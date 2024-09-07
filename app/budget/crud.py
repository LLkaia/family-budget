from typing import cast

from sqlmodel.ext.asyncio.session import AsyncSession

from budget.models import Budget, BudgetBase
from users.models import User


async def create_budget_with_user(session: AsyncSession, budget_data: BudgetBase, user: User) -> Budget:
    """Create a new Budget with User."""
    budget = Budget.model_validate(budget_data, update={"users": [user]})
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return cast(Budget, budget)
