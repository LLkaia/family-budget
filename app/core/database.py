from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings


config = get_settings()
engine = create_async_engine(config.db_conn_string, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

PSQL_QUERY_ALLOWED_MAX_ARGS = 32767


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
