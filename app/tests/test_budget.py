import uuid

from httpx import AsyncClient

from budget.schemas import BudgetFixture
from users.schemas import UserFixture


async def test_create_budget(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"name": "Monthly Expenses", "balance": 1000.0}
    response = await client.post("/budget", json=data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json["name"] == data["name"], response_json
    assert response_json["balance"] == data["balance"], response_json


async def test_create_budget_neg_balance(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"name": "Monthly Expenses", "balance": -500.0}
    response = await client.post("/budget", json=data, headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "balance" in response_json["detail"][0]["loc"], response_json


async def test_create_budget_not_auth(client: AsyncClient) -> None:
    data = {"name": "Monthly Expenses", "balance": 1000.0}
    response = await client.post("/budget", json=data)
    response_json = response.json()
    assert response.status_code == 401, response_json


async def test_get_my_budgets(client: AsyncClient, test_user: UserFixture, test_budget: BudgetFixture) -> None:
    response = await client.get("/budget", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert isinstance(response_json, list), response_json
    assert len(response_json) == 1, response_json
    assert uuid.UUID(response_json[0]["id"]) == test_budget.id, response_json


async def test_get_my_budgets_not_auth(client: AsyncClient) -> None:
    response = await client.get("/budget")
    response_json = response.json()
    assert response.status_code == 401, response_json
