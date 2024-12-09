import uvicorn
from fastapi import FastAPI

from budget.routes import router as budget_router
from stocks.routes import router as stocks_router
from users.routes import router as users_router


app = FastAPI(docs_url="/")


# @app.on_event("startup")
# async def on_startup() -> None:
#     """Init database on startup."""
#     await init_db()


app.include_router(users_router, prefix="/account", tags=["account"])
app.include_router(budget_router, prefix="/budget", tags=["budget"])
app.include_router(stocks_router, prefix="/stocks", tags=["stocks"])


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
