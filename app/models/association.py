from sqlalchemy import Column, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.core.db import Base

book_authors_association = Table(
    'book_authors', Base.metadata,
    Column('book_id', PG_UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True),
    Column('author_id', PG_UUID(as_uuid=True), ForeignKey('authors.id'), primary_key=True)
)

book_genres_association = Table(
    'book_genres', Base.metadata,
    Column('book_id', PG_UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True),
    Column('genre_id', PG_UUID(as_uuid=True), ForeignKey('genres.id'), primary_key=True)
)