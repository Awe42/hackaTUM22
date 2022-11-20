from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class OrderModel(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    side: str = Field(...)
    qty: int = Field(...)
    security: str = Field(...)
    price: float = Field(...)
    user: str = Field(...)
    date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True


class MatchModel(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    buyer: str = Field(...)
    seller: str = Field(...)
    security: str = Field(...)
    qty: int = Field(...)
    price: float = Field(...)
    date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
