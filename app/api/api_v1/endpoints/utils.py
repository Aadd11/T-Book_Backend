from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.schemas.genre import GenrePublic
from app.schemas.author import AuthorPublic
from app.crud import crud_genre, crud_author
from typing import List

router = APIRouter()

@router.get("/genres", response_model=List[GenrePublic])
async def get_all_genres(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of all unique genres.
    """
    genres = await crud_genre.get_genres(db, skip=skip, limit=limit)
    return genres


@router.get("/authors", response_model=List[AuthorPublic])
async def get_all_authors(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of all unique authors.
    """
    authors = await crud_author.get_authors(db, skip=skip, limit=limit)
    return authors