from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.api_v1.router import api_router
from app.core.config import settings
from app.core.db import engine, Base
from app.core.es import check_and_create_es_index, close_es_client

async def init_db():
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    print("Checking Elasticsearch connection and index...")
    await check_and_create_es_index()
    yield
    print("Shutting down...")
    await close_es_client()
    print("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}

from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)