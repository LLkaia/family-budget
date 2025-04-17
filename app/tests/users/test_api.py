from httpx import AsyncClient

from users.schemas import UserFixture


async def test_register_correct_data(client: AsyncClient) -> None:
    data = {"email": "test1@example.com", "password": "Example12345@", "full_name": "Test"}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 201, response_json
    assert response_json == {"message": "User 'Test' successfully registered."}, response_json


async def test_register_short_password(client: AsyncClient) -> None:
    data = {"email": "test2@example.com", "password": "shrt12$", "full_name": "Test"}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 422, response_json


async def test_register_existing_email(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"email": test_user.email, "password": test_user.password, "full_name": test_user.full_name}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 400, response_json
    assert response_json["detail"] == "Email already registered.", response_json


async def test_register_invalid_email_format(client: AsyncClient) -> None:
    data = {"email": "invalid-email", "password": "Example12345@", "full_name": "Test"}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "email" in response_json["detail"][0]["loc"], response_json


async def test_register_missing_email(client: AsyncClient) -> None:
    data = {"password": "Example12345@", "full_name": "Test"}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "email" in response.json()["detail"][0]["loc"], response_json


async def test_register_missing_password(client: AsyncClient) -> None:
    data = {"email": "test2@example.com", "full_name": "Test"}
    response = await client.post("/account/register", json=data)
    response_json = response.json()
    assert response.status_code == 422, response_json
    assert "password" in response.json()["detail"][0]["loc"], response_json


async def test_login_successful(client: AsyncClient, test_user: UserFixture) -> None:
    data = {"username": test_user.email, "password": test_user.password}
    response = await client.post("/account/login", data=data)
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["token_type"] == "bearer", response_json


async def test_login_incorrect_credentials(client: AsyncClient) -> None:
    data = {"username": "wrong@example.com", "password": "wrongpassword"}
    response = await client.post("/account/login", data=data)
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_token_valid(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.post("/account/verify", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["message"] == "Token is valid.", response_json


async def test_token_invalid(client: AsyncClient) -> None:
    headers = {"Authorization": "Bearer dummy-token"}
    response = await client.post("/account/verify", headers=headers)
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_auth_user_profile(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.get("/account", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["email"] == test_user.email, response_json
    assert response_json["full_name"] == test_user.full_name, response_json
    assert response_json["is_superuser"] is True, response_json


async def test_not_auth_user_profile(client: AsyncClient) -> None:
    response = await client.get("/account")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_not_auth_logout(client: AsyncClient) -> None:
    response = await client.post("/account/logout")
    response_json = response.json()
    assert response.status_code == 401, response_json
    assert response_json["detail"] == "Not authenticated", response_json


async def test_logout(client: AsyncClient, test_user: UserFixture) -> None:
    response = await client.post("/account/logout", headers=test_user.get_headers())
    response_json = response.json()
    assert response.status_code == 200, response_json
    assert response_json["message"] == "Successfully logged out.", response_json
    response = await client.post("/account/verify", headers=test_user.get_headers())
    assert response.status_code == 401, response_json
