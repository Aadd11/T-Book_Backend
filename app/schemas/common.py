from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic
import uuid

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    results: List[T]
    total_hits: int
    page: int
    page_size: int

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

class UUIDSchema(BaseModel):
    id: uuid.UUID