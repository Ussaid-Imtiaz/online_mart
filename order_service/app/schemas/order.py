from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    total_price: float

class OrderRead(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    total_price: float
    order_date: datetime
