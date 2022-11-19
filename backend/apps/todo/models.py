from typing import Optional
import uuid
from pydantic import BaseModel, Field


class OrderModel(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    type: str = Field(...)
    side: str = Field(...)
    qty: int = Field(...)
    security: str = Field(...)
    price: float = Field(...)
    user: str = Field(...)

    class Config:
        allow_population_by_field_name = True
