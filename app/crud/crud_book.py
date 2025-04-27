from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from app.models.book import Book
from app.models.author import Author
from app.models.genre import Genre
from app.schemas.book import BookCreate, BookUpdate
from .crud_author import get_author, get_or_create_author
from .crud_genre import get_genre, get_or_create_genre
import uuid
from typing import List, Optional

def _get_book_query_with_relationships():
    return select(Book).options(
        selectinload(Book.authors),
        selectinload(Book.genres)
    )

async def get_book(db: AsyncSession, book_id: uuid.UUID) -> Optional[Book]:
    result = await db.execute(
        _get_book_query_with_relationships().where(Book.id == book_id)
    )
    return result.scalars().first()

async def get_book_by_isbn13(db: AsyncSession, isbn13: str) -> Optional[Book]:
    if not isbn13: return None
    result = await db.execute(
        _get_book_query_with_relationships().where(Book.isbn_13 == isbn13)
    )
    return result.scalars().first()

async def find_existing_book(db: AsyncSession, book_data: BookCreate) -> Optional[Book]:
    if book_data.isbn_13:
        existing = await get_book_by_isbn13(db, book_data.isbn_13)
        if existing:
            return existing

    if book_data.title and book_data.author_names:
         first_author_name = book_data.author_names[0]
         stmt = _get_book_query_with_relationships().join(Book.authors).where(
             Book.title == book_data.title,
             Author.name == first_author_name
         )
         if book_data.year_published:
             stmt = stmt.where(Book.year_published.between(
                 book_data.year_published - 1, book_data.year_published + 1)
             )
         result = await db.execute(stmt)
         return result.scalars().first()

    return None


async def create_book(db: AsyncSession, book: BookCreate) -> Book:
    db_book = Book(**book.model_dump(exclude={'author_ids', 'genre_ids', 'author_names', 'genre_names'}))

    db_book.authors = []
    if book.author_ids:
        for author_id in book.author_ids:
            author = await get_author(db, author_id)
            if author:
                db_book.authors.append(author)
    elif book.author_names:
        for name in book.author_names:
            author = await get_or_create_author(db, name)
            db_book.authors.append(author)

    db_book.genres = []
    if book.genre_ids:
        for genre_id in book.genre_ids:
            genre = await get_genre(db, genre_id)
            if genre:
                db_book.genres.append(genre)
    elif book.genre_names:
        for name in book.genre_names:
            genre = await get_or_create_genre(db, name)
            db_book.genres.append(genre)

    db.add(db_book)
    await db.flush()
    await db.refresh(db_book, attribute_names=['authors', 'genres'])
    return db_book

async def update_book(db: AsyncSession, db_book: Book, book_in: BookUpdate) -> Book:
    update_data = book_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key not in ['author_ids', 'genre_ids']:
             setattr(db_book, key, value)

    if book_in.author_ids is not None:
        db_book.authors = []
        for author_id in book_in.author_ids:
            author = await get_author(db, author_id)
            if author:
                db_book.authors.append(author)

    if book_in.genre_ids is not None:
        db_book.genres = []
        for genre_id in book_in.genre_ids:
            genre = await get_genre(db, genre_id)
            if genre:
                db_book.genres.append(genre)

    db.add(db_book)
    await db.flush()
    await db.refresh(db_book, attribute_names=['authors', 'genres'])
    return db_book

async def get_books(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Book]:
    result = await db.execute(
        _get_book_query_with_relationships().offset(skip).limit(limit)
    )
    return result.scalars().unique().all()