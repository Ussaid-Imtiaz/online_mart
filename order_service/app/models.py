from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name : str
    product_name: str
    quantity: int
    total_price: Optional[float] = None

