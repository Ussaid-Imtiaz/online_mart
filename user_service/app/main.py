from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated, AsyncGenerator
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel import Session
from .models import User
from .api import auth
from .db import crud
from app.db.crud import create_tables, get_session

@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    # await create_topic()
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="User Service", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8016",
            "description": "Development Server"
        }
    ]
    ) 

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.post("/register/", response_model=None)
async def register_user(session: Annotated[Session, Depends(get_session)] , user: auth.UserCreate):
    hashed_password = auth.pwd_context.hash(user.password)
    db_user = await crud.create_user(session=session, username=user.username, email=user.email, hashed_password=hashed_password)
    return {"message": "User registered successfully"}

@app.post("/token", response_model=auth.Token)
async def login_for_access_token(session: Annotated[Session, Depends(get_session)], form_data: auth.OAuth2PasswordRequestForm = Depends()):
    user = await auth.authenticate_user(session,form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(auth.get_current_user)):
    return current_user



