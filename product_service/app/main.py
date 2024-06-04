import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import SQLModel, Session, select, Session
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from app import settings
from typing import Annotated
from app import product_pb2
from app.db import create_tables, get_session
from app.kafka_utils import create_topic, get_kafka_producer
from app.models import Product, ProductCreate, ProductUpdate, User, get_current_active_user
from aiokafka import AIOKafkaProducer
from jose import JWTError, jwt

# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    # asyncio.create_task(consume_message("products", settings.BOOTSTRAP_SERVER))
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    await create_topic()
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="My Products", 
    version="1.0",
    # servers=[
    #     {
    #         "url": "http://127.0.0.1:8000",
    #         "description": "Development Server"
    #     }
    # ]
) 


SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(SQLModel):
    username: Optional[str] = None

class User(SQLModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

async def get_current_user(token: Annotated [str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code="401",
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    # In a real-world application, you should verify the user from the database here
    user = User(username=username, email="test@example.com", full_name="Test User", disabled=False)
    return user

async def get_current_active_user(current_user: Annotated[User , Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.get("/secure-endpoint")
async def secure_endpoint(current_user: Annotated[User , Depends(get_current_user)] ):
    return {"message": "This is a secure endpoint", "user": current_user.username}

        
# Step-9: Create all endpoints of Product app
@app.get("/")
async def root():
    return {"Hello" : "This is Product Service."}

@app.get("/products", response_model=List[Product])
async def get_all(session:Annotated[Session, Depends(get_session)], 
                  current_user: Annotated[User, Depends(get_current_active_user)]
                  ):
    
    statement = select(Product).where(Product.user_id == current_user['id'])
    products = session.exec(statement).all()
    if products:
        return products
    else:
        raise HTTPException(status_code=404, detail="No Product Found")

@app.get("/products/{id}", response_model=Product )
async def get_one(id: int ,session:Annotated[Session, Depends(get_session)],
                  current_user:Annotated[User, Depends(get_current_active_user)]):
    # SQLModel queries: Select Product of given id and execute first result
    user_products = session.exec(select(Product).where(Product.user_id == current_user.id)).all()
    matched_product = next((product for product in user_products if product.id == id),None)
    if matched_product:
        return matched_product
    else:
        raise HTTPException(status_code=404, detail="No Product Found")
    

# Post endpoint
@app.post("/products/", response_model=Product)
async def create_product(
    product: ProductCreate, 
    session: Annotated[Session, Depends(get_session)], 
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
    current_user:Annotated[User, Depends(get_current_active_user)]
    )->Product:
        
    # Associate product with the current user
    db_product = Product.model_validate(product)
    db_product.user_id = current_user.id

    # Serialize using Protobuf 
    product_protobuf = product_pb2.Product(
        id = product.id, 
        description = product.description, 
        price = product.price, 
        stock = product.stock, 
        user_id=current_user.id
    )
    print(f"Product Protobuf : {product_protobuf}")
    serialized_product = product_protobuf.SerializeToString()
    print(f"Serialized Data : {serialized_product}")

    # Produce message to Kafka
    await producer.send_and_wait("products", serialized_product)

    # Add product to the database
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@app.put("/products/{product_id}", response_model=Product )
async def edit_one(
    product_id: int, 
    product_update: ProductUpdate,
    current_user:Annotated[User, Depends(get_current_active_user)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)], 
    session:Annotated[Session, Depends(get_session)]
    ):

    # Fetch the product from the database
    db_product = session.get(Product, product_id)

    if not db_product:
        raise HTTPException(status_code="404", detail="Product not found")
    
    # Check if the current user is the owner of the product
    if db_product.user_id != current_user.id:
        raise HTTPException(status_code="403", detail="Not authorized to update this product")
    
    # Update the product fields
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    # Serialize the updated product using Protobuf
    product_protobuf = product_pb2.Product(
        id=db_product.id,
        description=db_product.description,
        price=db_product.price,
        stock=db_product.stock,
        user_id=db_product.user_id
    )
    print(f"Updated Product Protobuf: {product_protobuf}")
    serialized_product = product_protobuf.SerializeToString()
    print(f"Serialized Updated Data: {serialized_product}")

    # Produce the updated message to Kafka
    await producer.send_and_wait("products", serialized_product)
    
    # Save the changes to the database
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    
    return db_product

    
@app.delete("/products/{product_id}", response_model=Product)
async def delete_product(
    product_id: int,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> Product:
    # Fetch the product from the database
    db_product = session.get(Product, product_id)
    
    if not db_product:
        raise HTTPException(status_code="404", detail="Product not found")
    
    # Check if the current user is the owner of the product
    if db_product.user_id != current_user.id:
        raise HTTPException(status_code="404", detail="Not authorized to delete this product")
    
    # Serialize the product to indicate deletion using Protobuf
    product_protobuf = product_pb2.Product(
        id=db_product.id,
        description=db_product.description,
        price=db_product.price,
        stock=db_product.stock,
        user_id=db_product.user_id
    )
    serialized_product = product_protobuf.SerializeToString()

    # Produce the delete message to Kafka
    await producer.send_and_wait("products_deleted", serialized_product)
    
    # Delete the product from the database
    session.delete(db_product)
    session.commit()
    
    return db_product



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
        return {"message": "Welcome to the Product Service!"}

    uvicorn.run(app, host="0.0.0.0", port=8001)







