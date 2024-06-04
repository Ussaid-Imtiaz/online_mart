from pydantic import BaseModel
from typing import Optional

class InventoryCreate(BaseModel):
    product_id: int
    quantity: int

class InventoryRead(BaseModel):
    id: int
    product_id: int
    quantity: int
