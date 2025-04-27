from pydantic import BaseModel, Field
from .common import BaseSchema, UUIDSchema

class AuthorBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)

class AuthorCreate(AuthorBase):
    pass

class Author(AuthorBase, UUIDSchema):
    pass

class AuthorPublic(AuthorBase, UUIDSchema):
    pass