from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.infrastructure.database.db_helper import db_helper
from src.infrastructure.database.base import Base
from src.intarfaces.api import (
    auth,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app=FastAPI(title="Authorized service", lifespan=lifespan)
app.include_router(auth.router)

if __name__=="__main__":
    uvicorn.run("run.main:app", host="0.0.0.0", port=8000, reload=True)


