from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select, text
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings


config = get_settings()
engine = create_async_engine(config.db_conn_string, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

PSQL_QUERY_ALLOWED_MAX_ARGS = 32767

SQL_FILES_TO_RUN_ON_STARTUP = [
    "./migrations/create_audit_triggers.sql",
]


async def get_db() -> AsyncSession:
    """Get session object."""
    async with SessionLocal() as session:
        yield session
        await session.commit()


async def is_db_alive() -> bool:
    """Check if database is up and running."""
    try:
        async with SessionLocal() as session:
            await session.exec(select(1))
        return True
    except OSError:
        return False


async def init_db() -> None:
    """Initialize tables in database."""
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


async def run_sql_file(path: str) -> None:
    """Run SQL statements from file."""
    async with SessionLocal() as session:
        async for sql_statement in read_sql_statements_from_file(path):
            await session.exec(text(sql_statement))
        await session.commit()


async def read_sql_statements_from_file(path: str, delimiter: str = "--") -> AsyncGenerator[str, None]:
    """Read SQL statements from file.

    Prepare SQL statements from file separated by
    delimiter. This is workaround to be able to
    run multiple statements from one file one by one.
    :param path: File path to SQL statements.
    :param delimiter: Delimiter between statements.
    :yield: SQL statements.
    """
    buffer: list[str] = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            if line.strip() == delimiter:
                if buffer:
                    yield "".join(buffer).strip()
                    buffer = []
            else:
                buffer.append(line)
    if buffer:
        yield "".join(buffer).strip()
