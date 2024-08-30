from functools import lru_cache

from pydantic import computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contains settings for project.

    Attributes:
        postgres_password: password for postgres connection
        postgres_host: host for postgres connection
        postgres_port: port for postgres connection
        postgres_user: user for postgres connection
        postgres_db: database for postgres connection
        secret_key: secret key for application security
        algorithm: algorithm for application security
        access_token_expire_minutes: minutes for token expiration
        db_conn_string: postgres connection string
    """

    model_config = SettingsConfigDict(env_file=".env")

    postgres_password: str
    postgres_user: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

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


@lru_cache
def get_settings() -> Settings:
    """Get settings object for project."""
    return Settings()
