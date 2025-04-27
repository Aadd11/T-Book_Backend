from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.author import Author
from app.schemas.author import AuthorCreate
import uuid
from typing import List, Optional

async def get_author(db: AsyncSession, author_id: uuid.UUID) -> Optional[Author]:
    result = await db.execute(select(Author).where(Author.id == author_id))
    return result.scalars().first()

async def get_author_by_name(db: AsyncSession, name: str) -> Optional[Author]:
    result = await db.execute(select(Author).where(Author.name == name))
    return result.scalars().first()

async def get_or_create_author(db: AsyncSession, name: str) -> Author:
    author = await get_author_by_name(db, name)
    if not author:
        author = Author(name=name)
        db.add(author)
        await db.flush()
        await db.refresh(author)
    return author

async def get_authors(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Author]:
    result = await db.execute(select(Author).offset(skip).limit(limit))
    return result.scalars().all()

async def create_author(db: AsyncSession, author: AuthorCreate) -> Author:
    db_author = Author(name=author.name)
    db.add(db_author)
    await db.flush()
    await db.refresh(db_author)
    return db_author