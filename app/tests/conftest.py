import asyncio
from asyncio import AbstractEventLoop
from dataclasses import dataclass, field
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings
from core.database import get_db
from main import app
from users.crud import create_user
from users.schemas import UserCreate


config = get_settings()
admin_engine = create_async_engine(config.db_conn_string, isolation_level="AUTOCOMMIT")
test_engine = create_async_engine(config.test_db_conn_string)
TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database() -> AsyncGenerator[None, None]:
    """Set up test database for all tests."""
    # create test db
    async with admin_engine.connect() as connection:
        try:
            await connection.execute(text(f"CREATE DATABASE {config.postgres_test_db}"))
        except ProgrammingError:
            pass
    # create tables before all tests started
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # drop all tables after tests finished
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@dataclass
class UserFixture:
    """User fixture for tests."""

    email: str = "test@example.com"
    password: str = "test12345"
    full_name: str = "Test User"
    token: str = field(default="", init=False)

    def get_headers(self) -> dict[str, str]:
        """Return the headers with the authorization token."""
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture(scope="session")
async def test_user() -> AsyncGenerator[UserFixture, None]:
    """Create test user."""
    user = UserFixture()
    async with TestSessionLocal() as session:
        await create_user(session, UserCreate(email=user.email, password=user.password, full_name=user.full_name))
    yield user


@pytest.fixture
async def db() -> AsyncSession:
    """Get test session object."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide TestClient and override db connection."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()