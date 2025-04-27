from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.association import book_authors_association

class Author(Base):
    __tablename__ = "authors"
    name = Column(String, unique=True, index=True, nullable=False)

    books = relationship(
        "Book",
        secondary=book_authors_association,
        back_populates="authors"
    )

    def __repr__(self):
        return f"<Author(id={self.id}, name='{self.name}')>"