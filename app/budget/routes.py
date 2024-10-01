import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from budget.crud import (
    add_user_to_budget,
    create_budget_with_user,
    create_category_and_add_to_budget,
    create_predefined_category,
    get_budget_by_id_with_current_user,
    get_predefined_categories,
    perform_transaction_per_budget,
    remove_budget,
    remove_category_from_budget,
    remove_predefined_category,
    remove_user_from_budget,
    update_budget,
    update_category,
)
from budget.schemas import (
    BudgetCreate,
    BudgetDetails,
    BudgetList,
    BudgetUpdate,
    CategoryCreate,
    CategoryUpdate,
    PredefinedCategoryCreate,
    PredefinedCategoryList,
    TransactionCreate,
)
from core.database import get_db
from exceptions import ItemNotExistsException
from models import Budget, Category, PredefinedCategory, User
from users.auth import current_superuser, current_user
from users.crud import get_user_by_email
from users.schemas import UserBase


router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget: BudgetCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Budget:
    """Create new budget for current user."""
    return await create_budget_with_user(session, budget, user)


@router.get("/")
async def get_my_budgets(user: Annotated[User, Depends(current_user)]) -> BudgetList:
    """Get current user budgets."""
    return BudgetList(data=user.budgets)


@router.post("/predefined-categories", status_code=status.HTTP_201_CREATED, dependencies=[Depends(current_superuser)])
async def create_predefined_categories(
    category: PredefinedCategoryCreate, session: Annotated[AsyncSession, Depends(get_db)]
) -> PredefinedCategory:
    """Create new predefined category."""
    try:
        return await create_predefined_category(session, category)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists.")


@router.get("/predefined-categories", dependencies=[Depends(current_user)])
async def list_predefined_categories(
    session: Annotated[AsyncSession, Depends(get_db)], offset: int = 0, limit: int = 100
) -> PredefinedCategoryList:
    """Retrieve predefined category."""
    return await get_predefined_categories(session, offset, limit)


@router.delete(
    "/predefined-categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def delete_predefined_categories(
    category_id: Annotated[uuid.UUID, Path(title="Predefined category ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Create new predefined category."""
    try:
        await remove_predefined_category(session, category_id)
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


@router.get("/{budget_id}", response_model=BudgetDetails, response_model_exclude_none=True)
async def get_budget(budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)]) -> Budget:
    """Get budget by id."""
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    session: Annotated[AsyncSession, Depends(get_db)],
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
) -> None:
    """Delete budget."""
    await remove_budget(session, budget)


@router.put("/{budget_id}", response_model=BudgetDetails, response_model_exclude_none=True)
async def modify_budget(
    session: Annotated[AsyncSession, Depends(get_db)],
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    new_data: BudgetUpdate,
) -> Budget:
    """Update budget with new data."""
    return await update_budget(session, budget, new_data)


@router.post("/{budget_id}/users", response_model=BudgetDetails, response_model_exclude_none=True)
async def add_new_user_to_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    user_data: UserBase,
) -> Budget:
    """Add new user to budget."""
    user = await get_user_by_email(session, user_data.email)
    if not user:
        raise HTTPException(detail="User not found.", status_code=status.HTTP_404_NOT_FOUND)
    return await add_user_to_budget(session, budget, user)


@router.delete("/{budget_id}/users", response_model=BudgetDetails, response_model_exclude_none=True)
async def delete_user_from_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    user_data: UserBase,
) -> Budget:
    """Delete user from budget."""
    user = await get_user_by_email(session, user_data.email)
    if not user or user not in budget.users:
        raise HTTPException(detail="User not found.", status_code=status.HTTP_404_NOT_FOUND)
    return await remove_user_from_budget(session, budget, user)


@router.post("/{budget_id}/categories", response_model_exclude_none=True)
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


@router.delete("/{budget_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_from_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[uuid.UUID, Path(title="Category ID for specific budget")],
) -> None:
    """Delete category from specific budget."""
    try:
        await remove_category_from_budget(session, budget, category_id)
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


@router.put("/{budget_id}/categories/{category_id}", response_model_exclude_none=True)
async def modify_category_for_budget(
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[uuid.UUID, Path(title="Category ID for specific budget")],
    category_data: CategoryUpdate,
) -> Category:
    """Modify category with new data."""
    try:
        return await update_category(session, budget, category_id, category_data)
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


@router.post("/{budget_id}/categories/{category_id}/transactions")
async def perform_transaction(
    session: Annotated[AsyncSession, Depends(get_db)],
    budget: Annotated[Budget, Depends(get_budget_by_id_with_current_user)],
    category_id: Annotated[uuid.UUID, Path(title="Category ID for specific budget")],
    transaction_data: TransactionCreate,
) -> Budget:
    """Perform transaction per budget per category."""
    try:
        return await perform_transaction_per_budget(session, budget, category_id, transaction_data)
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
