from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.genre import Genre
from app.schemas.genre import GenreCreate
import uuid
from typing import List, Optional

async def get_genre(db: AsyncSession, genre_id: uuid.UUID) -> Optional[Genre]:
    result = await db.execute(select(Genre).where(Genre.id == genre_id))
    return result.scalars().first()

async def get_genre_by_name(db: AsyncSession, name: str) -> Optional[Genre]:
    result = await db.execute(select(Genre).where(Genre.name == name))
    return result.scalars().first()

async def get_or_create_genre(db: AsyncSession, name: str) -> Genre:
    genre = await get_genre_by_name(db, name)
    if not genre:
        genre = Genre(name=name)
        db.add(genre)
        await db.flush()
        await db.refresh(genre)
    return genre

async def get_genres(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Genre]:
    result = await db.execute(select(Genre).offset(skip).limit(limit))
    return result.scalars().all()

async def create_genre(db: AsyncSession, genre: GenreCreate) -> Genre:
    db_genre = Genre(name=genre.name)
    db.add(db_genre)
    await db.flush()
    await db.refresh(db_genre)
    return db_genre