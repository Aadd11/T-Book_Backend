from sqlalchemy import Column, Table, ForeignKey, String, Integer, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from app.core.db import Base
from app.models.association import (
    book_authors_association,
    book_genres_association
)

book_authors_association = Table(
    'book_authors', Base.metadata,
    Column('book_id', PG_UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True),
    Column('author_id', PG_UUID(as_uuid=True), ForeignKey('authors.id'), primary_key=True)
    ,extend_existing=True
)

book_genres_association = Table(
    'book_genres', Base.metadata,
    Column('book_id', PG_UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True),
    Column('genre_id', PG_UUID(as_uuid=True), ForeignKey('genres.id'), primary_key=True)
    ,extend_existing=True
)


class Book(Base):
    __tablename__ = "books"

    title = Column(String, index=True, nullable=False)
    year_published = Column(Integer, index=True, nullable=True)
    summary = Column(Text, nullable=True)
    age_rating = Column(String, nullable=True)
    language = Column(String, index=True, nullable=True)
    book_size_pages = Column(Integer, nullable=True)
    book_size_description = Column(String, nullable=True)
    average_rating = Column(Float, index=True, nullable=True)
    rating_details = Column(JSONB, nullable=True)
    source_url = Column(String, nullable=True)
    isbn_10 = Column(String(10), index=True, nullable=True)
    isbn_13 = Column(String(13), unique=True, index=True, nullable=True)

    authors = relationship(
        "Author",
        secondary=book_authors_association,
        back_populates="books",
        lazy="selectin"
    )
    genres = relationship(
        "Genre",
        secondary=book_genres_association,
        back_populates="books",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}')>"