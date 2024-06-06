from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated, AsyncGenerator
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.auth import EXPIRY_TIME, authenticate_user, create_access_token, current_user, get_user_from_db, hash_password, oauth_scheme
from app.db import create_tables, get_session
from app.models import Register_User, Token, User
from app.kafka_utils import create_topic, kafka_producer
from app import settings

# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    await create_topic()
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="My Todos", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8000",
            "description": "Development Server"
        }
    ]
    ) 

@app.get("/")
async def read_user():
    return {"message": "Welcome to dailyDo todo app User Page"}

@app.post("/register")
async def regiser_user (new_user:Annotated[Register_User, Depends()],
                        session:Annotated[Session, Depends(get_session)]):
    
    db_user = get_user_from_db(session, new_user.username, new_user.email)
    if db_user:
        raise HTTPException(status_code=409, detail="User with these credentials already exists")
    user = User(username = new_user.username,
                email = new_user.email,
                password = hash_password(new_user.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": f""" User with {user.username} successfully registered """}

@app.post('/login', response_model=Token)
async def login(
    form_data:Annotated[OAuth2PasswordRequestForm, Depends()],
    session:Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(kafka_producer)],
    user: User
    ):

    user = authenticate_user (form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    expire_time = timedelta(minutes=EXPIRY_TIME)
    access_token = create_access_token({"sub":form_data.username}, expire_time)

    user_proto = user_pb2.User()
    user_dict = {field: getattr(user_proto, field) for field in user_proto.dict()}
    serialized_user = user_dict.SerializeToString()
    await producer.send_and_wait(settings.KAFKA_USER_TOPIC, serialized_user)

    return Token(access_token=access_token, token_type="bearer")

@app.get('/me')
async def user_profile (current_user:Annotated[User, Depends(current_user)]):

    return current_user

