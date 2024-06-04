# main.py
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select, SQLModel, create_engine, Session, Field
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app import settings
from typing import Annotated
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app import product_pb2
import json

from services.user_service.auth import current_user
from services.user_service.models import User

  
# Step-1: Create Database on Neon
# Step-2: Create .env file for environment variables
# Step-3: Create setting.py file for encrypting DatabaseURL

# Create a variable using url as parameter and add psycopg with postgresql in url.
connection_string: str = str(   # Convert URL into string
    settings.DATABASE_URL
    ).replace(      
    "postgresql", 
    "postgresql+psycopg"
    )         

# Step-4: Create engine using sqlmodel to create connection between SQLModel and Postgresql
engine = create_engine( 
    connection_string, 
    # connect_args={"sslmode": "require"}, # use ssl(secure socket layer) to encrypt communication with DB.
    pool_recycle=300, # SQL engine use pool of connections to minimise time of each request, recycle upto 5 mins (300seconds)
    pool_size=10, 
    echo=True
    )  

# Step-5: Create function for table creation. 
def create_tables() -> None:
    SQLModel.metadata.create_all(engine)    # Contents of Schema (with tables) is registered with metadata attribute of sqlmodel

# Step-6: Create function for session management 
def get_session():
    with Session(engine) as session:        # With will auto close session.
        yield session                       # yield (generator function) will iterate over sessions.


# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    
    asyncio.create_task(consume_message("products", settings.BOOTSTRAP_SERVER))
    
    print("Creating Tables")
    create_tables()
    print("Tables Created")

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


# Step-8: Create model class using tables to use as schema in APIs 
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    price: float
    stock: int

# Step-9: Create all endpoints of Product app
@app.get("/")
async def root():
    return {"Hello" : "This is Product Service."}


@app.get("/products", response_model=list[Product]) # List of Products will be returned.
async def get_all(session:Annotated[Session, Depends(get_session)],
                  current_user:Annotated[User, Depends(current_user)]):
    # SQLModel queries: Select all Products and execute all
    statement = select(Product).where(Product.user_id == current_user.id)
    Products = session.exec(statement).all()
    if Products:
        return Products
    else:
        raise HTTPException(status_code=404, detail="No Product Found")


@app.get("/products/{id}", response_model=Product )
async def get_one(id: int ,session:Annotated[Session, Depends(get_session)],
                  current_user:Annotated[User, Depends(current_user)]):
    # SQLModel queries: Select Product of given id and execute first result
    user_products = session.exec(select(Product).where(Product.user_id == current_user.id)).all()
    matched_product = next((product for product in user_products if product.id == id),None)
    if matched_product:
        return matched_product
    else:
        raise HTTPException(status_code=404, detail="No Product Found")


        
@app.put("/products/{id}", response_model=Product )
async def edit_one(id: int, edited_product_by_user:Product, session:Annotated[Session, Depends(get_session)]):
    # SQLModel queries: Select Product of given id and execute first result
    statement = select(Product).where(Product.id == id)
    product_for_edit = session.exec(statement).first()
    if product_for_edit:
        product_for_edit.name = edited_product_by_user.name    # edited_Product_by_user.content coming from function parameter which user will input
        product_for_edit.description = edited_product_by_user.description
        product_for_edit.price = edited_product_by_user.price
        product_for_edit.stock = edited_product_by_user.stock  # edited_Product_by_user..is_completed coming from function parameter which user will input
        # for posting new edited Product 
        session.add(product_for_edit)
        session.commit()
        session.refresh(product_for_edit) # to return from database
        return product_for_edit
    else:
        raise HTTPException(status_code=404, detail="No Product Found")
    
@app.delete("/products{id}")
async def delete_product(id: int, session:Annotated[Session, Depends(get_session)]):
    statement = select(Product).where(Product.id == id)
    product_to_delete = session.exec(statement).first()
    if product_to_delete:
        session.delete(product_to_delete)
        session.commit()
        return {"message": "Product Deleted Successfully"}
    else:
        raise HTTPException(status_code=404, detail="No Product Found")


# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

# Post endpoint
@app.post("/products/", response_model=Product)
async def create_product(product: Product, session: Annotated[Session, Depends(get_session)], 
                         producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
                         current_user:Annotated[User, Depends(current_user)]
                         )->Product:
        
        # Serialize using Protobuf 
        product_protobuf = product_pb2.Product(id = product.id, description = product.description, price = product.price, stock = product.stock, user_id=current_user.id)
        print(f"Product Protobuf : {product_protobuf}")
        serialized_product = product_protobuf.SerializeToString()
        print(f"Serialized Data : {serialized_product}")


        # Produce message
        await producer.send_and_wait("products", serialized_product)
        # session.add(product)
        # session.commit()
        # session.refresh(product)
        return product

@app.post('/todos/', response_model=Todo)
async def create_todo(current_user:Annotated[User, Depends(current_user)],
                      todo: Todo_Create, 
                      session: Annotated[Session, Depends(get_session)]):
    
    new_todo = Todo(content=todo.content, user_id=current_user.id)
    
    session.add(new_todo)
    session.commit()
    session.refresh(new_todo)
    return new_todo

async def consume_message(topic, bootstrap_servers):
    # create a consumer instance
    consumer = AIOKafkaConsumer(
        topic, 
        bootstrap_servers = bootstrap_servers,
        group_id = "my-group",
        auto_offset_reset = 'earliest'
    )

    # Start the consumer
    await consumer.start()
    try:
        # Continuasly listen to message
        async for message in consumer:
            print(f'Received message: {message.value} on topic {message.topic}')
            new_product = product_pb2.Product()
            new_product.ParseFromString(message.value)
            print(f'\n\m Consumer Deserialized Data : {new_product}')
        # Add code to process messages

    finally:
        await consumer.stop()












@app.put('/todos/{id}')
async def edit_todo(id: int, 
                    todo: Todo_Edit,
                    current_user:Annotated[User, Depends(current_user)], 
                    session: Annotated[Session, Depends(get_session)]):
    
    user_todos = session.exec(select(Todo).where(Todo.user_id == current_user.id)).all()
    existing_todo = next((todo for todo in user_todos if todo.id == id),None)

    if existing_todo:
        existing_todo.content = todo.content
        existing_todo.is_completed = todo.is_completed
        session.add(existing_todo)
        session.commit()
        session.refresh(existing_todo)
        return existing_todo
    else:
        raise HTTPException(status_code=404, detail="No task found")


@app.delete('/todos/{id}')
async def delete_todo(id: int,
                      current_user:Annotated[User, Depends(current_user)],
                      session: Annotated[Session, Depends(get_session)]):
    
    user_todos = session.exec(select(Todo).where(Todo.user_id == current_user.id)).all()
    todo = next((todo for todo in user_todos if todo.id == id),None)
    
    if todo:
        session.delete(todo)
        session.commit()
        # session.refresh(todo)
        return {"message": "Task successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="No task found")








