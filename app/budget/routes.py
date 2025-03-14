from datetime import date
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
    get_categories_by_budget_and_user,
    get_category_by_id_with_user,
    get_list_transactions,
    get_predefined_categories,
    get_transaction_by_id_with_user,
    perform_transaction_per_category,
    remove_budget,
    remove_category,
    remove_predefined_category,
    remove_transaction,
    remove_user_from_budget,
    retrieve_budgets_by_user,
    update_budget,
    update_category,
    update_transaction,
)
from budget.schemas import (
    BudgetCreate,
    BudgetDetails,
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
from core.database import get_db
from exceptions import ItemNotExistsException, ParameterMissingException
from models import Budget, Category, PredefinedCategory, Transaction, User
from users.auth import current_superuser, current_user
from users.crud import get_user_by_email, get_user_by_id
from users.schemas import UserBase
from utils import PeriodFrom


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget: BudgetCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Budget:
    """Create new budget for current user."""
    return await create_budget_with_user(session, budget, user)


@router.get("")
async def get_my_budgets(
    user: Annotated[User, Depends(current_user)], session: Annotated[AsyncSession, Depends(get_db)]
) -> list[Budget]:
    """Get current user budgets."""
    return await retrieve_budgets_by_user(session, user)


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
    "/predefined-categories/{id_}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def delete_predefined_categories(
    id_: Annotated[int, Path(title="Predefined category ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Create new predefined category."""
    try:
        await remove_predefined_category(session, id_)
    except ItemNotExistsException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


@router.get("/{budget_id}", response_model=BudgetDetails, response_model_exclude_none=True)
async def get_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Budget:
    """Get budget by id."""
    budget = await get_budget_by_id_with_current_user(budget_id, session, user, detailed=True)
    if budget:
        return budget
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    """Delete budget."""
    budget = await get_budget_by_id_with_current_user(budget_id, session, user)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")
    await remove_budget(session, budget)


@router.patch("/{budget_id}", response_model_exclude_none=True)
async def modify_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    new_data: BudgetUpdate,
) -> Budget:
    """Update budget with new data."""
    budget = await get_budget_by_id_with_current_user(budget_id, session, user)
    if budget:
        return await update_budget(session, budget, new_data)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")


@router.post("/{budget_id}/users", response_model=BudgetDetails, response_model_exclude_none=True)
async def add_new_user_to_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    user_data: UserBase,
) -> Budget:
    """Add new user to budget."""
    user_to_add = await get_user_by_email(session, user_data.email)
    if not user_to_add:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    budget = await get_budget_by_id_with_current_user(budget_id, session, user, detailed=True)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")
    if user_to_add in budget.users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    return await add_user_to_budget(session, budget, user_to_add)


@router.delete("/{budget_id}/users/{user_id}", response_model=BudgetDetails, response_model_exclude_none=True)
async def delete_user_from_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    user_id: Annotated[int, Path(title="User id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Budget:
    """Delete user from budget."""
    budget = await get_budget_by_id_with_current_user(budget_id, session, user, detailed=True)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")

    user_to_delete = await get_user_by_id(session, user_id)
    if not user_to_delete or user_to_delete not in budget.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return await remove_user_from_budget(session, budget, user_to_delete)


@router.post("/{budget_id}/categories", response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def add_new_category_to_budget(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    category: CategoryCreate,
) -> Category:
    """Create category and add it to budget."""
    budget = await get_budget_by_id_with_current_user(budget_id, session, user, detailed=True)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")

    try:
        return await create_category_and_add_to_budget(session, budget, category)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists.")


@router.get("/{budget_id}/categories", response_model_exclude_none=True)
async def get_budget_categories(
    budget_id: Annotated[int, Path(title="Budget id")],
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    income: bool | None = None,
    transactions: bool | None = None,
    period: PeriodFrom | None = None,
) -> list[CategoryWithAmount]:
    """Get list of categories from budget."""
    try:
        return await get_categories_by_budget_and_user(budget_id, user.id, session, income, transactions, period)
    except ParameterMissingException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    category_id: Annotated[int, Path(title="Category ID for specific budget")],
) -> None:
    """Delete category from specific budget."""
    category = await get_category_by_id_with_user(session, user, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    await remove_category(session, category)


@router.patch("/categories/{category_id}", response_model_exclude_none=True)
async def modify_category(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    category_id: Annotated[int, Path(title="Category ID for specific budget")],
    category_data: CategoryUpdate,
) -> Category:
    """Modify category with new data."""
    category = await get_category_by_id_with_user(session, user, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return await update_category(session, category, category_data)


@router.post("/categories/{category_id}/transactions")
async def perform_transaction(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    category_id: Annotated[int, Path(title="Category ID for specific budget")],
    transaction_data: TransactionCreate,
) -> Budget:
    """Perform transaction per budget per category."""
    category = await get_category_by_id_with_user(session, user, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    budget = await get_budget_by_id_with_current_user(category.budget_id, session, user)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.")
    if budget.balance < transaction_data.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough money.")
    return await perform_transaction_per_category(session, budget, category, transaction_data)


@router.get("/{budget_id}/transactions")
async def get_budget_transactions(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    budget_id: Annotated[int, Path(title="Budget id")],
    date_start: date | None = None,
    date_end: date | None = None,
    category_name_filter: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> TransactionList:
    """Get list of transactions for budget."""
    return await get_list_transactions(
        session, budget_id, user.id, date_start, date_end, category_name_filter, offset, limit
    )


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    transaction_id: Annotated[int, Path(title="Transaction ID")],
) -> None:
    """Delete transaction by ID."""
    transaction = await get_transaction_by_id_with_user(session, user, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    await remove_transaction(session, transaction)


@router.patch("/transactions/{transaction_id}")
async def modify_transaction(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    transaction_id: Annotated[int, Path(title="Transaction ID")],
    transaction_data: TransactionUpdate,
) -> Transaction:
    """Update transaction by ID."""
    transaction = await get_transaction_by_id_with_user(session, user, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    try:
        return await update_transaction(session, transaction, transaction_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
