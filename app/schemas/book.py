from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
import uuid
from .common import BaseSchema, UUIDSchema, PaginatedResponse
from .author import AuthorPublic
from .genre import GenrePublic

class BookBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=500)
    year_published: Optional[int] = Field(None, ge=0, le=3000)
    summary: Optional[str] = None
    age_rating: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=50)
    book_size_pages: Optional[int] = Field(None, ge=0)
    book_size_description: Optional[str] = Field(None, max_length=100)
    average_rating: Optional[float] = Field(None, ge=0, le=10)
    rating_details: Optional[List[Dict[str, Any]]] = None
    source_url: Optional[str] = Field(None, max_length=2048)
    isbn_10: Optional[str] = Field(None, min_length=10, max_length=10)
    isbn_13: Optional[str] = Field(None, min_length=13, max_length=13)


class BookCreate(BookBase):
    author_ids: Optional[List[uuid.UUID]] = None
    genre_ids: Optional[List[uuid.UUID]] = None
    author_names: Optional[List[str]] = None
    genre_names: Optional[List[str]] = None

class BookUpdate(BookBase):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author_ids: Optional[List[uuid.UUID]] = None
    genre_ids: Optional[List[uuid.UUID]] = None


class Book(BookBase, UUIDSchema):
    authors: List[AuthorPublic] = []
    genres: List[GenrePublic] = []


class BookPublic(BookBase, UUIDSchema):
    authors: List[AuthorPublic] = []
    genres: List[GenrePublic] = []

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string (e.g., author, title, description)")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class SearchResponse(BaseModel):
    task_id: Optional[str] = None
    message: str
    initial_results: Optional[List[BookPublic]] = None
    total_hits: Optional[int] = None