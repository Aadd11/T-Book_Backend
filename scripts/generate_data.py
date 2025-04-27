import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import asyncio
import random
import uuid
from faker import Faker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.book import Book
from app.models.author import Author
from app.models.genre import Genre
from app.crud.crud_book import create_book
from app.crud.crud_author import get_or_create_author
from app.crud.crud_genre import get_or_create_genre
from app.schemas.book import BookCreate
from app.services.search_service import bulk_index_books

fake = Faker()

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def generate_authors(db: AsyncSession, count: int) -> list[Author]:
    authors = []
    print(f"Generating {count} authors...")
    for _ in range(count):
        name = fake.name()
        result = await db.execute(select(Author).where(Author.name == name))
        existing = result.scalars().first()
        if not existing:
            author = Author(name=name)
            db.add(author)
            authors.append(author)
    await db.flush()
    print(f"Generated {len(authors)} unique authors.")
    all_authors_result = await db.execute(select(Author))
    return all_authors_result.scalars().all()


async def generate_genres(db: AsyncSession, genres_list: list[str]) -> list[Genre]:
    genres = []
    print(f"Generating/Fetching {len(genres_list)} genres...")
    for name in genres_list:
        result = await db.execute(select(Genre).where(Genre.name == name))
        existing = result.scalars().first()
        if not existing:
            genre = Genre(name=name)
            db.add(genre)
            genres.append(genre)
        else:
            genres.append(existing)
    await db.flush()
    print(f"Ensured {len(genres)} genres exist.")
    return genres

async def generate_books(db: AsyncSession, count: int, authors: list[Author], genres: list[Genre]):
    books_to_create = []
    print(f"Generating {count} books...")
    for i in range(count):
        if not authors or not genres:
            print("Warning: No authors or genres available to assign.")
            break

        cover_seed = i + 1
        cover_url = f"https://picsum.photos/seed/{cover_seed}/300/450"

        book_data = BookCreate(
            title=fake.catch_phrase() + " " + random.choice(["Chronicles", "Secrets", "Journey", "Legacy", "Tales"]),
            year_published=random.randint(1950, 2025),
            summary=fake.paragraph(nb_sentences=5),
            age_rating=random.choice(["All", "7+", "13+", "16+", "18+", None]),
            language=random.choice(["English", "Spanish", "French", "German", "Japanese"]),
            book_size_pages=random.randint(150, 1200),
            average_rating=round(random.uniform(2.5, 5.0), 1) if random.random() > 0.1 else None,
            isbn_13=f"978{random.randint(1000000000, 9999999999)}" if random.random() > 0.05 else None,
            cover_url=cover_url,
            author_names=[author.name for author in random.sample(authors, k=random.randint(1, min(3, len(authors))))],
            genre_names=[genre.name for genre in random.sample(genres, k=random.randint(1, min(4, len(genres))))]
        )
        books_to_create.append(book_data)

        if (i + 1) % 100 == 0:
             print(f"Prepared {i+1}/{count} books...")

    created_books_db = []
    for book_data in books_to_create:
        try:
             created_book = await create_book(db, book_data)
             created_books_db.append(created_book)
             if len(created_books_db) % 50 == 0:
                  print(f"Saved {len(created_books_db)} books to DB...")
        except Exception as e:
            print(f"Error creating book '{book_data.title}': {e}. Skipping.")
            await db.rollback()

    print(f"Created {len(created_books_db)} books in the database.")
    return created_books_db


async def main(num_authors: int = 50, num_books: int = 500):
    genres_list = [
        "Fiction", "Science Fiction", "Fantasy", "Mystery", "Thriller", "Romance",
        "Historical Fiction", "Non-Fiction", "Biography", "History", "Science",
        "Self-Help", "Adventure", "Children's", "Young Adult", "Poetry", "Horror"
    ]

    created_books = []
    async with AsyncSessionLocal() as session:
        async with session.begin():
            authors = await generate_authors(session, num_authors)
            genres = await generate_genres(session, genres_list)

            created_books = await generate_books(session, num_books, authors, genres)

    print("\nDatabase population complete.")

    if created_books:
        print(f"\nStarting Elasticsearch indexing for {len(created_books)} books...")
        await bulk_index_books(created_books)
        print("Elasticsearch indexing complete.")
    else:
        print("\nNo books were created, skipping Elasticsearch indexing.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate sample book data.")
    parser.add_argument('--authors', type=int, default=50, help='Number of authors to generate.')
    parser.add_argument('--books', type=int, default=500, help='Number of books to generate.')
    args = parser.parse_args()

    asyncio.run(main(num_authors=args.authors, num_books=args.books))