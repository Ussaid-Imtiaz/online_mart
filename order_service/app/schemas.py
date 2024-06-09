from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class OrderCreate(BaseModel):
    user_name : str
    product_name: str
    quantity: int

class OrderRead(BaseModel):
    id: int
    user_name : str
    product_name: str
    quantity: int
    total_price: Optional[float]



