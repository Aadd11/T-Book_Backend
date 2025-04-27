from pydantic import BaseModel, Field
from .common import BaseSchema, UUIDSchema

class GenreBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)

class GenreCreate(GenreBase):
    pass

class Genre(GenreBase, UUIDSchema):
    pass

class GenrePublic(GenreBase, UUIDSchema):
    pass