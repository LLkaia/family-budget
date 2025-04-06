from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from budget.routes import router as budget_router
from core.config import get_settings
from core.database import SQL_FILES_TO_RUN_ON_STARTUP, run_sql_file
from stocks.routes import router as stocks_router
from users.routes import router as users_router


config = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Perform logic on startup and shutdown."""
    # await init_db()
    for file_path in SQL_FILES_TO_RUN_ON_STARTUP:
        await run_sql_file(file_path)
    yield


app = FastAPI(docs_url="/", title="Family Budget API", version=config.api_version, lifespan=lifespan)


app.include_router(users_router, prefix="/account", tags=["account"])
app.include_router(budget_router, prefix="/budget", tags=["budget"])
app.include_router(stocks_router, prefix="/stocks", tags=["stocks"])


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
