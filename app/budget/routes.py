from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from budget.crud import create_budget_with_user
from budget.models import Budget, BudgetBase
from core.database import get_db
from users.auth import current_user
from users.models import User


router = APIRouter()


@router.post("/create", response_model=Budget)
async def create_budget(
    budget: BudgetBase, session: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(current_user)]
) -> Budget:
    """Create new budget for current user."""
    budget = await create_budget_with_user(session, budget, user)
    return budget
