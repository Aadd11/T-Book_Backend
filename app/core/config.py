import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import warnings

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Book Search Service"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/bookdb")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "postgresql://user:password@localhost:5432/bookdb")


    ELASTICSEARCH_URL: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    ELASTICSEARCH_USERNAME: str | None = os.getenv("ELASTICSEARCH_USERNAME")
    ELASTICSEARCH_PASSWORD: str | None = os.getenv("ELASTICSEARCH_PASSWORD")
    ELASTICSEARCH_INDEX_NAME: str = "books_index"

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    EXTERNAL_SEARCH_API_BASE_URL: str | None = os.getenv("EXTERNAL_SEARCH_API_BASE_URL")

    class Config:
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    if not s.EXTERNAL_SEARCH_API_BASE_URL:
        warnings.warn(
            "EXTERNAL_SEARCH_API_BASE_URL environment variable is not set. "
            "External search functionality will be disabled or may fail.",
            RuntimeWarning
        )
    return s

settings = get_settings()