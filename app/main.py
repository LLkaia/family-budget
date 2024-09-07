import uvicorn
from fastapi import FastAPI

from users.routes import router as users_router


app = FastAPI()


# @app.on_event("startup")
# async def on_startup() -> None:
#     """Init database on startup."""
#     await init_db()


app.include_router(users_router, prefix="/account", tags=["account"])


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
