
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.association import book_genres_association

class Genre(Base):
    __tablename__ = "genres"
    name = Column(String, unique=True, index=True, nullable=False)

    books = relationship(
        "Book",
        secondary=book_genres_association,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(id={self.id}, name='{self.name}')>"