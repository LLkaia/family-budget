from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from budget.crud import create_budget_with_user, create_predefined_category, get_predefined_categories
from budget.models import Budget, BudgetBase, CategoryBase, PredefinedCategories, PredefinedCategory
from core.database import get_db
from users.auth import current_superuser, current_user
from users.models import User


router = APIRouter()


@router.post("/create", response_model=Budget)
async def create_budget(
    budget: BudgetBase, session: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(current_user)]
) -> Budget:
    """Create new budget for current user."""
    budget = await create_budget_with_user(session, budget, user)
    return budget


@router.post("/predefined-categories", response_model=PredefinedCategory, dependencies=[Depends(current_superuser)])
async def create_predefined_categories(
    category: CategoryBase, session: Annotated[AsyncSession, Depends(get_db)]
) -> PredefinedCategory:
    """Create new predefined category."""
    category = await create_predefined_category(session, category)
    return category


@router.get("/predefined-categories", response_model=PredefinedCategories, dependencies=[Depends(current_user)])
async def list_predefined_categories(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> PredefinedCategories:
    """Retrieve predefined category."""
    categories = await get_predefined_categories(session, offset, limit)
    return categories
