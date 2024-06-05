from typing import Optional
from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int

class ProductRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int
