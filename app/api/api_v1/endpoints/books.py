from fastapi import APIRouter, HTTPException, Depends, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.genre import GenrePublic
from app.schemas.author import AuthorPublic
from app.core.db import get_db
from app.schemas.book import BookPublic, PaginatedResponse
from app.services.search_service import search_books_in_es
from typing import List, Optional
import uuid

from app.tasks.scrape import process_search_query

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[BookPublic])
async def get_books_from_search(
    q: Optional[str] = Query(None, description="Search query string (searches title, authors, summary, etc.)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("relevance", description="Sort criteria (e.g., relevance, rating_desc, year_asc, title_asc)"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    genre: Optional[str] = Query(None, description="Filter by genre name"),
    min_year: Optional[int] = Query(None, description="Filter by minimum publication year"),
    max_year: Optional[int] = Query(None, description="Filter by maximum publication year"),
    min_rating: Optional[float] = Query(None, description="Filter by minimum average rating"),
    language: Optional[str] = Query(None, description="Filter by language"),
):
    """
    Retrieves a list of books based on search query, filters, and sorting
    using the Elasticsearch index.
    Also triggers a background Celery task to update results from external sources if a query 'q' is provided.
    """
    filters = {
        "author": author,
        "genre": genre,
        "min_year": min_year,
        "max_year": max_year,
        "min_rating": min_rating,
        "language": language,
    }
    active_filters = {k: v for k, v in filters.items() if v is not None}

    results, total_hits = await search_books_in_es(
        query=q,
        filters=active_filters,
        sort_by=sort_by,
        page=page,
        page_size=page_size
    )

    if q and q.strip():
        task = process_search_query.delay(q)
        print(f"Dispatched Celery task {task.id} for query: '{q}' from /books endpoint.")
    public_results = [
        BookPublic(
            **{k: v for k, v in result.items() if k not in ['authors', 'genres']},
            authors=[AuthorPublic(**a) for a in result.get("authors", []) if isinstance(a, dict)],
            genres=[GenrePublic(**g) for g in result.get("genres", []) if isinstance(g, dict)]
        )
        for result in results
    ]


    return PaginatedResponse[BookPublic](
        results=public_results,
        total_hits=total_hits,
        page=page,
        page_size=page_size
    )


from app.crud import crud_book

@router.get("/{book_id}", response_model=BookPublic)
async def read_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single book by its ID from the database.
    """
    db_book = await crud_book.get_book(db=db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return db_book