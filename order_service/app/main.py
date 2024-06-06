from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from .models.order import Order
from app.schemas.order import OrderCreate, OrderRead
from app.db import get_session, init_db
from fastapi.middleware.cors import CORSMiddleware
import json
from kafka import KafkaConsumer
from concurrent.futures import ThreadPoolExecutor
import inventory_pb2
from google.protobuf.json_format import Parse

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

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.post("/orders/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(*, session: Session = Depends(get_session), order: OrderCreate):
    new_order = Order(**order.dict())
    session.add(new_order)
    session.commit()
    session.refresh(new_order)
    return new_order

@app.get("/orders/{order_id}", response_model=OrderRead)
def read_order(*, session: Session = Depends(get_session), order_id: int):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/orders/", response_model=list[OrderRead])
def read_orders(*, session: Session = Depends(get_session)):
    orders = session.exec(select(Order)).all()
    return orders

@app.put("/orders/{order_id}", response_model=OrderRead)
def update_order(*, session: Session = Depends(get_session), order_id: int, order: OrderCreate):
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in order.dict().items():
        setattr(db_order, key, value)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(*, session: Session = Depends(get_session), order_id: int):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    session.delete(order)
    session.commit()
    return




# Function to handle inventory updates
def handle_inventory_update(message):
    try:
        inventory_update = Parse(message.value, inventory_pb2.InventoryUpdate())
        print(f"Received inventory update: {inventory_update}")
        # Handle the inventory update as needed
    except Exception as e:
        print(f"Error handling message: {e}")

# Setup Kafka consumer
consumer = KafkaConsumer(
    'inventory_updates',
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

executor = ThreadPoolExecutor(max_workers=1)

def consume_messages():
    for message in consumer:
        executor.submit(handle_inventory_update, message)

if __name__ == "__main__":
    # Run the consumer in a separate thread
    import threading
    consumer_thread = threading.Thread(target=consume_messages)
    consumer_thread.start()

    # Start the FastAPI app
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Order Service!"}

    uvicorn.run(app, host="0.0.0.0", port=8002)
