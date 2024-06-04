from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from .models.user import User
from .schemas.user import UserCreate, UserRead
from .db import get_session, init_db
from .hashing import hash_password, verify_password
from fastapi.middleware.cors import CORSMiddleware

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

@app.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(*, session: Session = Depends(get_session), user: UserCreate):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@app.post("/users/login")
def login(*, session: Session = Depends(get_session), user: UserCreate):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"message": "Login successful"}


import json
from kafka import KafkaConsumer
from concurrent.futures import ThreadPoolExecutor
import inventory_pb2
from google.protobuf.json_format import Parse

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
        return {"message": "Welcome to the User Service!"}

    uvicorn.run(app, host="0.0.0.0", port=8000)
