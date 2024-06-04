from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from kafka import KafkaProducer
import inventory_pb2
from google.protobuf.json_format import MessageToJson
from .models.inventory import Inventory
from .schemas.inventory import InventoryCreate, InventoryRead
from .db import get_session, init_db
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.post("/inventory/", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
def create_inventory(*, session: Session = Depends(get_session), inventory: InventoryCreate):
    new_inventory = Inventory(**inventory.dict())
    session.add(new_inventory)
    session.commit()
    session.refresh(new_inventory)

    # Create and send Kafka message
    inventory_update = inventory_pb2.InventoryUpdate(
        product_id=new_inventory.product_id,
        quantity=new_inventory.quantity
    )
    producer.send('inventory_updates', MessageToJson(inventory_update))

    return new_inventory

@app.get("/inventory/{inventory_id}", response_model=InventoryRead)
def read_inventory(*, session: Session = Depends(get_session), inventory_id: int):
    inventory = session.get(Inventory, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory

@app.get("/inventory/", response_model=list[InventoryRead])
def read_inventory_list(*, session: Session = Depends(get_session)):
    inventory = session.exec(select(Inventory)).all()
    return inventory

@app.put("/inventory/{inventory_id}", response_model=InventoryRead)
def update_inventory(*, session: Session = Depends(get_session), inventory_id: int, inventory: InventoryCreate):
    db_inventory = session.get(Inventory, inventory_id)
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    for key, value in inventory.dict().items():
        setattr(db_inventory, key, value)
    session.add(db_inventory)
    session.commit()
    session.refresh(db_inventory)
    return db_inventory

@app.delete("/inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(*, session: Session = Depends(get_session), inventory_id: int):
    inventory = session.get(Inventory, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    session.delete(inventory)
    session.commit()
    return
