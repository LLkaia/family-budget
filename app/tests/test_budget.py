import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

from budget.schemas import BudgetFixture
from models import User
from tests.conftest import TestSessionLocal
from users.crud import create_user, remove_user
from users.schemas import UserCreate, UserFixture


@pytest.fixture
async def budget_user(client: AsyncClient) -> AsyncGenerator[User, None]:
    async with TestSessionLocal() as session:
        created_user = await create_user(
            session, UserCreate(email="test_budget@example.com", password="test12345", full_name="Budget User")
        )
    yield created_user
    async with TestSessionLocal() as session:
        await remove_user(session, created_user)


async def test_create_budget(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"name": "Monthly Expenses", "balance": 1000.0}
    response = await client.post("/budget", json=data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json["name"] == data["name"], response_json
    assert response_json["balance"] == data["balance"], response_json


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


async def test_get_my_budgets(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    response = await client.get("/budget", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert isinstance(response_json, list), response_json
    assert len(response_json) == 1, response_json
    assert response_json[0]["id"] == str(test_budget.id), response_json


async def test_get_my_budgets_not_auth(client: AsyncClient) -> None:
    response = await client.get("/budget")
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_get_budget(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    response = await client.get(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == str(test_budget.id), response_json
    assert response_json["name"] == test_budget.name, response_json
    assert response_json["balance"] == test_budget.balance, response_json
    assert response_json["users"][0]["email"] == test_user.email, response_json


async def test_get_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.get(f"/budget/{uuid.uuid1()}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_get_budget_not_auth(client: AsyncClient, test_budget: BudgetFixture) -> None:
    response = await client.get(f"/budget/{test_budget.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


@pytest.mark.filterwarnings("ignore:DELETE")
async def test_delete_budget(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    response = await client.delete(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    assert response.status_code == 204, "Unexpected response code"
    follow_up_response = await client.get(f"/budget/{test_budget.id}", headers=test_user.get_headers())
    assert follow_up_response.status_code == 404, follow_up_response.json()


async def test_delete_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.delete(f"/budget/{uuid.uuid1()}", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_delete_budget_not_auth(client: AsyncClient, test_budget: BudgetFixture) -> None:
    response = await client.delete(f"/budget/{test_budget.id}")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_modify_budget(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    update_data = {"name": "Updated Budget", "balance": 1500}
    response = await client.put(f"/budget/{test_budget.id}", json=update_data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == str(test_budget.id), response_json
    assert response_json["name"] == update_data["name"], response_json
    assert response_json["balance"] == update_data["balance"], response_json


async def test_modify_budget_balance(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    update_data = {"balance": 1500}
    response = await client.put(f"/budget/{test_budget.id}", json=update_data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == str(test_budget.id), response_json
    assert response_json["name"] == test_budget.name, response_json
    assert response_json["balance"] == update_data["balance"], response_json


async def test_modify_budget_neg_balance(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture
) -> None:
    response = await client.put(f"/budget/{test_budget.id}", json={"balance": -1500}, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "balance" in response_json["detail"][0]["loc"], response_json


async def test_modify_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.put(
        f"/budget/{uuid.uuid1()}",
        json={"name": "Nonexistent Budget", "balance": 1000.0},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_modify_budget_not_auth(client: AsyncClient, test_budget: BudgetFixture) -> None:
    response = await client.put(f"/budget/{test_budget.id}", json={"name": "Unauthorized Update", "balance": 2000.0})
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_add_new_user_to_budget(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture, budget_user: User
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": budget_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == str(test_budget.id), response_json
    assert any(u["email"] == budget_user.email for u in response_json["users"]), response_json


async def test_add_new_user_to_budget_user_not_found(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": "nonexistent@example.com"}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_add_new_user_to_budget_budget_not_found(
    client: AsyncClient, test_user: UserFixture, budget_user: User
) -> None:
    response = await client.post(
        f"/budget/{uuid.uuid1()}/users", json={"email": budget_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_add_new_user_to_budget_user_already_exists(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture
) -> None:
    response = await client.post(
        f"/budget/{test_budget.id}/users", json={"email": test_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "User already exists.", response_json


async def test_add_new_user_to_budget_not_auth(client: AsyncClient, test_budget: BudgetFixture) -> None:
    response = await client.post(f"/budget/{test_budget.id}/users", json={"email": "test3@example.com"})
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_delete_user_from_budget(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    response = await client.request(
        "DELETE", f"/budget/{test_budget.id}/users", json={"email": test_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["id"] == str(test_budget.id), response_json
    assert not any(u["email"] == test_user.email for u in response_json["users"]), response_json


async def test_delete_user_from_budget_user_not_found(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture, budget_user: User
) -> None:
    response = await client.request(
        "DELETE",
        f"/budget/{test_budget.id}/users",
        json={"email": "imagine@example.com"},
        headers=test_user.get_headers(),
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_delete_user_from_budget_user_not_in_budget(
    client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture, budget_user: User
) -> None:
    response = await client.request(
        "DELETE", f"/budget/{test_budget.id}/users", json={"email": budget_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "User not found.", response_json


async def test_delete_user_from_budget_budget_not_found(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.request(
        "DELETE", f"/budget/{uuid.uuid1()}/users", json={"email": test_user.email}, headers=test_user.get_headers()
    )
    response_json = response.json()
    assert response.status_code == 404, response_json
    assert response_json["detail"] == "Budget not found.", response_json


async def test_delete_user_from_budget_not_auth(
    client: AsyncClient, test_budget: BudgetFixture, test_user: UserFixture
) -> None:
    response = await client.request("DELETE", f"/budget/{test_budget.id}/users", json={"email": test_user.email})
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json
