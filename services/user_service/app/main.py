from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Annotated, AsyncGenerator
from contextlib import asynccontextmanager
from services.user_service.app.db import get_session, create_tables
from services.user_service.app.hashing import hash_password, verify_password
from services.user_service.app.models import User
from services.user_service.app.schemas import UserCreate, UserRead


# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="Users Page", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8000",
            "description": "Development Server"
        }
    ]
    ) 

# Step-9: Create all endpoints of User Service
@app.get("/")
async def root():
    return {"message": "Welcome to the User Service!"}


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








