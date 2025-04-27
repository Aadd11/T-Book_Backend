from fastapi import APIRouter
from .endpoints import search, books, utils

api_router = APIRouter()

api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(books.router, prefix="/books", tags=["Books"])
api_router.include_router(utils.router, prefix="/utils", tags=["Utilities"])