from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from budget.routes import router as budget_router
from core.config import get_settings
from stocks.routes import router as stocks_router
from users.routes import router as users_router


config = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Perform logic on startup and shutdown."""
    # await init_db()
    yield


app = FastAPI(docs_url="/", title="Family Budget API", version=config.api_version, lifespan=lifespan)


app.include_router(users_router, prefix="/account", tags=["Account"])
app.include_router(budget_router, prefix="/budget", tags=["Budget"])
app.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])

app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allowed_origins,
    allow_methods=config.cors_allowed_methods,
    allow_headers=config.cors_allowed_headers,
)


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
