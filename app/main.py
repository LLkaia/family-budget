import uvicorn
from fastapi import FastAPI, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_db, init_db
from users.models import User


app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/")
async def root(session: AsyncSession = Depends(get_db)):
    return {"ping": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
