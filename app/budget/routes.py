import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from budget.crud import (
    create_budget_with_user,
    create_category_and_add_to_budget,
    create_predefined_category,
    get_budget_by_id_with_current_user,
    get_predefined_categories,
    remove_budget,
    remove_category_from_budget,
    remove_predefined_category,
)
from budget.models import (
    Budget,
    BudgetBase,
    BudgetsList,
    Category,
    CategoryBase,
    CategoryCreate,
    PredefinedCategories,
    PredefinedCategory,
)
from core.database import get_db
from exceptions import ItemNotExistsException
from users.auth import current_superuser, current_user
from users.models import BudgetDetails, Message, User


router = APIRouter()


@router.post("/", response_model=Budget)
async def create_budget(
    budget: BudgetBase, session: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(current_user)]
) -> Budget:
    """Create new budget for current user."""
    return await create_budget_with_user(session, budget, user)


@router.get("/", response_model=BudgetsList)
async def get_my_budgets(user: Annotated[User, Depends(current_user)]) -> BudgetsList:
    """Get current user budgets."""
    return BudgetsList(data=user.budgets)


@router.post("/predefined-categories", response_model=PredefinedCategory, dependencies=[Depends(current_superuser)])
async def create_predefined_categories(
    category: CategoryBase, session: Annotated[AsyncSession, Depends(get_db)]
) -> PredefinedCategory:
    """Create new predefined category."""
    try:
        return await create_predefined_category(session, category)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists.")


@router.get("/predefined-categories", response_model=PredefinedCategories, dependencies=[Depends(current_user)])
async def list_predefined_categories(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> PredefinedCategories:
    """Retrieve predefined category."""
    return await get_predefined_categories(session, offset, limit)


@router.delete(
    "/predefined-categories/{category_id}", response_model=Message, dependencies=[Depends(current_superuser)]
)
async def delete_predefined_categories(
    category_id: Annotated[uuid.UUID, Path(title="Predefined category ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Message:
    """Create new predefined category."""
    try:
        await remove_predefined_category(session, category_id)
        return Message(message="Category successfully deleted.")
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


@router.get("/{budget_id}", response_model=BudgetDetails)
async def get_budget(budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)]) -> Budget:
    """Get budget by id."""
    return budget


@router.delete("/{budget_id}", response_model=Message)
async def delete_budget(
    session: Annotated[AsyncSession, Depends(get_db)],
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
) -> Message:
    """Delete budget."""
    await remove_budget(session, budget)
    return Message(message="Budget successfully deleted.")


@router.post("/{budget_id}/categories", response_model=Category)
async def add_new_category_to_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    category: CategoryCreate,
) -> Category:
    """Create category and add it to budget."""
    try:
        return await create_category_and_add_to_budget(session, budget, category)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists.")


@router.delete("/{budget_id}/categories/{category_id}", response_model=Message)
async def delete_category_from_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[uuid.UUID, Path(title="Category ID for specific budget")],
) -> Message:
    """Delete category from specific budget."""
    try:
        await remove_category_from_budget(session, budget, category_id)
        return Message(message="Category successfully deleted from budget.")
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
