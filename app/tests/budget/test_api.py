from datetime import date
from decimal import Decimal
from typing import AsyncGenerator, cast

import pytest
from httpx import AsyncClient

from budget.crud import (
    create_budget_with_user,
    create_category_and_add_to_budget,
    create_predefined_category,
    perform_transaction_per_category,
    remove_budget,
    remove_category,
    remove_predefined_category,
)
from budget.schemas import BudgetPublic, CategoryCreate, PredefinedCategoryCreate, TransactionCreate
from exceptions import ItemNotExistsException
from models import Budget, Category, PredefinedCategory, User
from tests.conftest import test_db
from users.crud import create_user, get_user_by_email, remove_user
from users.schemas import UserFixture


@pytest.fixture
async def test_budget(test_user: UserFixture, client: AsyncClient) -> AsyncGenerator[Budget, None]:
    """Create test budget for user fixture."""
    async with test_db() as session:
        user = await get_user_by_email(session, test_user.email)
        created_budget = await create_budget_with_user(
            session, BudgetPublic(name="Test Budget", balance=20000, id=1000), cast(User, user)
        )
    yield created_budget
    async with test_db() as session:
        await remove_budget(session, created_budget)


@pytest.fixture
async def test_category(test_budget: Budget) -> AsyncGenerator[Category, None]:
    """Create test category for Test Budget."""
    async with test_db() as session:
        category = await create_category_and_add_to_budget(
            session, test_budget, CategoryCreate(name="food", category_restriction=5000, is_income=False)
        )
        await create_category_and_add_to_budget(
            session, test_budget, CategoryCreate(name="salary", category_restriction=20000, is_income=True)
        )
    yield category
    async with test_db() as session:
        await remove_category(session, category)


@pytest.fixture
async def test_transactions(test_budget: Budget, test_category: Category) -> None:
    """Perform test transactions for category."""
    today = date.today()
    async with test_db() as session:
        transactions = [
            (TransactionCreate(amount=100, date_performed=today), test_category),
            (TransactionCreate(amount=300, date_performed=date(today.year, today.month, 1)), test_category),
            (TransactionCreate(amount=50, date_performed=date(today.year, 1, 1)), test_category),
        ]
        for transactions, category in transactions:
            await perform_transaction_per_category(session, test_budget, category, transactions)


@pytest.fixture
async def budget_user(client: AsyncClient) -> AsyncGenerator[UserFixture, None]:
    user_fixture = UserFixture(email="test_budget@example.com", password="Test12345@", full_name="Budget User", id=2000)
    async with test_db() as session:
        created_user = await create_user(session, user_fixture)
    yield user_fixture
    async with test_db() as session:
        await remove_user(session, created_user)


@pytest.fixture
async def test_predefined_category(client: AsyncClient) -> AsyncGenerator[PredefinedCategory, None]:
    async with test_db() as session:
        predefined_category = await create_predefined_category(session, PredefinedCategoryCreate(name="Test"))
    yield predefined_category
    async with test_db() as session:
        try:
            await remove_predefined_category(session, predefined_category.id)
        except ItemNotExistsException:
            pass


async def test_create_budget(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"name": "Monthly Expenses", "balance": 1000.0}
    response = await client.post("/budget", json=data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json["name"] == data["name"], response_json
    assert Decimal(response_json["balance"]) == data["balance"], response_json


async def test_create_budget_neg_balance(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.post(
        "/budget", json={"name": "Monthly Expenses", "balance": -500.0}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "balance" in response_json["detail"][0]["loc"], response_json


async def test_create_budget_not_auth(client: AsyncClient) -> None:
    response = await client.post("/budget", json={"name": "Monthly Expenses", "balance": 1000.0})
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_get_my_budgets(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    response = await client.get("/budget", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert isinstance(response_json, list), response_json
    assert len(response_json) == 1, response_json
    assert response_json[0]["id"] == test_budget.id, response_json


async def test_get_my_budgets_not_auth(client: AsyncClient) -> None:
    response = await client.get("/budget")
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_get_budget(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    response = await client.get(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_budget.id, response_json
    assert response_json["name"] == test_budget.name, response_json
    assert Decimal(response_json["balance"]) == test_budget.balance, response_json
    assert response_json["users"][0]["email"] == test_user.email, response_json


async def test_get_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.get("/budget/10", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_get_budget_not_auth(client: AsyncClient, test_budget: Budget) -> None:
    response = await client.get(f"/budget/{test_budget.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


@pytest.mark.filterwarnings("ignore:DELETE")
async def test_delete_budget(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    response = await client.delete(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    assert response.status_code == 204, "Unexpected response code"
    follow_up_response = await client.get(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    assert follow_up_response.status_code == 404, follow_up_response.json()


async def test_delete_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.delete("/budget/10", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_delete_budget_not_auth(client: AsyncClient, test_budget: Budget) -> None:
    response = await client.delete(f"/budget/{test_budget.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_modify_budget(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    update_data = {"name": "Updated Budget", "balance": 1500}
    response = await client.patch(f"/budget/{test_budget.id}", json=update_data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_budget.id, response_json
    assert response_json["name"] == update_data["name"], response_json
    assert Decimal(response_json["balance"]) == update_data["balance"], response_json


async def test_modify_budget_balance(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    update_data = {"balance": 1500}
    response = await client.patch(f"/budget/{test_budget.id}", json=update_data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_budget.id, response_json
    assert response_json["name"] == test_budget.name, response_json
    assert Decimal(response_json["balance"]) == update_data["balance"], response_json


async def test_modify_budget_neg_balance(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    response = await client.patch(f"/budget/{test_budget.id}", json={"balance": -1500}, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "balance" in response_json["detail"][0]["loc"], response_json


async def test_modify_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.patch(
        "/budget/10",
        json={"name": "Nonexistent Budget", "balance": 1000.0},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_modify_budget_not_auth(client: AsyncClient, test_budget: Budget) -> None:
    response = await client.patch(f"/budget/{test_budget.id}", json={"name": "Unauthorized Update", "balance": 2000.0})
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_add_new_user_to_budget(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, budget_user: UserFixture
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": budget_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_budget.id, response_json
    assert any(u["email"] == budget_user.email for u in response_json["users"]), response_json


async def test_add_new_user_to_budget_user_not_found(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": "nonexistent@example.com"}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_add_new_user_to_budget_budget_not_found(
    client: AsyncClient, test_user: UserFixture, budget_user: UserFixture
) -> None:
    response = await client.post("/budget/10/users", json={"email": budget_user.email}, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_add_new_user_to_budget_user_already_exists(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": test_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "User already exists.", response_json


async def test_add_new_user_to_budget_not_auth(client: AsyncClient, test_budget: Budget) -> None:
    response = await client.post(f"/budget/{test_budget.id}/users", json={"email": "test3@example.com"})
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_delete_user_from_budget(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    response = await client.delete(f"/budget/{test_budget.id}/users/{test_user.id}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_budget.id, response_json
    assert not any(u["email"] == test_user.email for u in response_json["users"]), response_json


async def test_delete_user_from_budget_user_not_found(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, budget_user: UserFixture
) -> None:
    response = await client.delete(f"/budget/{test_budget.id}/users/100", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_delete_user_from_budget_user_not_in_budget(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, budget_user: UserFixture
) -> None:
    response = await client.delete(f"/budget/{test_budget.id}/users/{budget_user.id}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_delete_user_from_budget_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.delete(f"/budget/10/users/{test_user.id}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_delete_user_from_budget_not_auth(
    client: AsyncClient, test_budget: Budget, test_user: UserFixture
) -> None:
    response = await client.delete(f"/budget/{test_budget.id}/users/{test_user.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_add_category_to_budget_success(client: AsyncClient, test_user: UserFixture, test_budget: Budget) -> None:
    test_category_data = {"name": "category", "description": "Test", "category_restriction": 100, "is_income": False}
    response = await client.post(
        f"/budget/{test_budget.id}/categories", json=test_category_data, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json["name"] == str(test_category_data["name"]).capitalize(), response_json
    assert Decimal(response_json["category_restriction"]) == test_category_data["category_restriction"], response_json
    assert response_json["description"] == test_category_data["description"], response_json
    assert response_json["is_income"] == test_category_data["is_income"], response_json
    assert response_json["budget_id"] == test_budget.id, response_json


async def test_add_category_to_budget_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.post(
        "/budget/10/categories",
        json={"name": "category", "description": "Test", "category_restriction": 100, "is_income": False},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_add_category_to_budget_duplicate_category(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, test_category: Category
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/categories",
        json={"name": test_category.name, "category_restriction": 500, "is_income": False},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "Category already exists.", response_json


async def test_add_category_to_budget_not_auth(client: AsyncClient, test_budget: Budget) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/categories",
        json={"name": "category", "description": "Test", "category_restriction": 100, "is_income": False},
    )
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_add_category_to_budget_negative_restriction(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/categories",
        json={"name": "category", "description": "Test", "category_restriction": -100, "is_income": False},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "category_restriction" in response_json["detail"][0]["loc"], response_json
    assert response_json["detail"][0]["msg"] == "Input should be greater than or equal to 0", response_json


async def test_add_category_to_budget_name_with_spaces(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/categories",
        json={"name": "category wrong", "description": "Test", "category_restriction": 100, "is_income": False},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert response_json["detail"]["msg"] == "Input should contain one word", response_json


@pytest.mark.filterwarnings("ignore:DELETE")
async def test_delete_category_success(client: AsyncClient, test_user: UserFixture, test_category: Category) -> None:
    response = await client.delete(f"/budget/categories/{test_category.id}", headers=test_user.get_headers())
    assert response.status_code == 204, response.text


async def test_delete_category_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.delete("/budget/categories/20", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Category not found.", response_json


async def test_delete_category_not_auth(client: AsyncClient, test_category: Category) -> None:
    response = await client.delete(f"/budget/categories/{test_category.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_modify_category_success(client: AsyncClient, test_user: UserFixture, test_category: Category) -> None:
    update_data = {
        "name": "Income",
        "category_restriction": 1500.0,
        "description": "Updated description",
        "is_income": True,
    }

    response = await client.patch(
        f"/budget/categories/{test_category.id}", json=update_data, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["name"] == update_data["name"], response_json
    assert Decimal(response_json["category_restriction"]) == update_data["category_restriction"], response_json
    assert response_json["description"] == update_data["description"], response_json
    assert response_json["is_income"] == update_data["is_income"], response_json


async def test_modify_category_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.patch(
        "/budget/categories/20",
        json={
            "name": "NonExistentCategory",
            "category_restriction": 100.0,
            "description": "Description",
            "is_income": False,
        },
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Category not found.", response_json


async def test_modify_category_not_auth(client: AsyncClient, test_category: Category) -> None:
    response = await client.patch(
        f"/budget/categories/{test_category.id}",
        json={
            "name": "NoAuthCategory",
            "category_restriction": 200.0,
            "description": "Unauthorized update",
            "is_income": True,
        },
    )
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_modify_category_invalid_restriction(
    client: AsyncClient, test_user: UserFixture, test_category: Category
) -> None:
    response = await client.patch(
        f"/budget/categories/{test_category.id}", json={"category_restriction": -50.0}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "category_restriction" in response_json["detail"][0]["loc"], response_json
    assert response_json["detail"][0]["msg"] == "Input should be greater than or equal to 0", response_json


async def test_perform_transaction_success(
    client: AsyncClient, test_user: UserFixture, test_category: Category, test_budget: Budget
) -> None:
    expected_balance = test_budget.balance - 200
    transaction_data = {"amount": 200, "date_performed": str(date.today())}
    response = await client.post(
        f"/budget/categories/{test_category.id}/transactions", json=transaction_data, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == test_category.budget_id, response_json
    assert Decimal(response_json["balance"]) == expected_balance, response_json


async def test_perform_transaction_negative_amount(
    client: AsyncClient, test_user: UserFixture, test_category: Category
) -> None:
    response = await client.post(
        f"/budget/categories/{test_category.id}/transactions",
        json={"amount": -100.0, "date_performed": str(date.today())},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "amount" in response_json["detail"][0]["loc"], response_json
    assert response_json["detail"][0]["msg"] == "Input should be greater than or equal to 0", response_json


async def test_perform_transaction_not_negative_balance(
    client: AsyncClient, test_user: UserFixture, test_category: Category
) -> None:
    response = await client.post(
        f"/budget/categories/{test_category.id}/transactions",
        json={"amount": 20100, "date_performed": str(date.today())},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "Not enough money.", response_json


async def test_get_budget_categories_success(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, test_category: Category
) -> None:
    response = await client.get(f"/budget/{test_budget.id}/categories", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert isinstance(response_json, list), response_json
    for category in response_json:
        assert "id" in category, category
        assert "name" in category, category
        assert "is_income" in category, category
        assert "category_restriction" in category, category


async def test_get_budget_categories_with_transactions_year(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, test_transactions: None
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories",
        headers=test_user.get_headers(),
        params={"transactions": True, "period": "year"},
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    for category in response_json:
        assert "total_amount" in category, category
        if category["name"] == "Food":
            assert Decimal(category["total_amount"]) == 450, category


async def test_get_budget_categories_with_transactions_month(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, test_transactions: None
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories",
        headers=test_user.get_headers(),
        params={"transactions": True, "period": "month"},
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    for category in response_json:
        assert "total_amount" in category, category
        if category["name"] == "Food":
            assert Decimal(category["total_amount"]) == 400, category


async def test_get_budget_categories_with_transactions_day(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget, test_transactions: None
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories",
        headers=test_user.get_headers(),
        params={"transactions": True, "period": "day"},
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    for category in response_json:
        assert "total_amount" in category, category
        if category["name"] == "Food":
            assert Decimal(category["total_amount"]) == 100, category


async def test_get_budget_categories_income_only(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories", headers=test_user.get_headers(), params={"income": True}
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    for category in response_json:
        assert category["is_income"] is True


async def test_get_budget_categories_expense_only(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories", headers=test_user.get_headers(), params={"income": False}
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    for category in response_json:
        assert category["is_income"] is False


async def test_get_budget_categories_budget_not_exist(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.get("/budget/10/categories", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json == [], response_json


async def test_get_budget_categories_missing_period(
    client: AsyncClient, test_user: UserFixture, test_budget: Budget
) -> None:
    response = await client.get(
        f"/budget/{test_budget.id}/categories", headers=test_user.get_headers(), params={"transactions": True}
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "'period_from' is required to get aggregated transactions amount."


async def test_create_predefined_category_success(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.post(
        "/budget/predefined-categories", json={"name": "category"}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json["name"] == "Category", response_json


async def test_create_predefined_category_already_exists(
    client: AsyncClient, test_user: UserFixture, test_predefined_category: PredefinedCategory
) -> None:
    response = await client.post(
        "/budget/predefined-categories", json={"name": test_predefined_category.name}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "Category already exists.", response_json


async def test_list_predefined_categories_success(
    client: AsyncClient, test_user: UserFixture, test_predefined_category: PredefinedCategory
) -> None:
    response = await client.get(
        "/budget/predefined-categories",
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert any(test_predefined_category.name == item["name"] for item in response_json["data"]), response_json


async def test_list_predefined_categories_no_auth(client: AsyncClient) -> None:
    response = await client.get("/budget/predefined-categories")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_delete_predefined_category_success(
    client: AsyncClient, test_user: UserFixture, test_predefined_category: PredefinedCategory
) -> None:
    response = await client.delete(
        f"/budget/predefined-categories/{test_predefined_category.id}",
        headers=test_user.get_headers(),
    )
    assert response.status_code == 204, response.json()
    response = await client.get(
        "/budget/predefined-categories",
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert not any(test_predefined_category.name == item["name"] for item in response_json["data"]), response_json


async def test_delete_predefined_category_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.delete(
        "/budget/predefined-categories/30",
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Category not found.", response_json
