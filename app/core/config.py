import os
from functools import lru_cache

from pydantic import computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contains settings for project.

    :arg postgres_password: password for postgres connection
    :arg postgres_host: host for postgres connection
    :arg postgres_port: port for postgres connection
    :arg postgres_user: user for postgres connection
    :arg postgres_db: database for postgres connection
    :arg postgres_test_db: test database for postgres connection
    :arg secret_key: secret key for application security
    :arg algorithm: algorithm for application security
    :arg access_token_expire_minutes: minutes for token expiration
    :arg db_conn_string: db connection string
    :arg test_db_conn_string: test db connection string
    :arg finnhub_api_key: api key for finnhub connection
    :arg api_version_file_path: path to file with api version
    :arg api_version: api version
    """

    model_config = SettingsConfigDict(env_file=".env")

    postgres_password: str
    postgres_user: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    postgres_test_db: str = "test_db"

    redis_host: str
    redis_port: int

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    api_version_file_path: str = "./.version"

    finnhub_api_key: str

    @computed_field  # type: ignore
    @property
    def db_conn_string(self) -> str:
        return str(
            MultiHostUrl.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @computed_field  # type: ignore
    @property
    def test_db_conn_string(self) -> str:
        return str(
            MultiHostUrl.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_test_db,
            )
        )

    @computed_field  # type: ignore
    @property
    def api_version(self) -> str:
        if os.path.exists(self.api_version_file_path):
            with open(self.api_version_file_path) as f:
                return f.read().strip()
        return "0.0.0"


@lru_cache
def get_settings() -> Settings:
    """Get settings object for project."""
    return Settings()
