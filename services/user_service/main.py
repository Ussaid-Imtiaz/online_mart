from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated, AsyncGenerator
from contextlib import asynccontextmanager
from user_service.auth import EXPIRY_TIME, authenticate_user, create_access_token, current_user, validate_refresh_token, create_refresh_token
from user_service.db import get_session, create_tables
from user_service.models import Todo, Todo_Create, Todo_Edit, Token, User
from user_service.route.user import user_router


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
    title="My Todos", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8000",
            "description": "Development Server"
        }
    ]
    ) 

# include user route in app to run from here
app.include_router(router=user_router)


# Step-9: Create all endpoints of todo app
@app.get("/")
async def root():
    return {"Hello" : "This is daily Do Todo app."}


@app.post('/token', response_model=Token)
async def login(form_data:Annotated[OAuth2PasswordRequestForm, Depends()],
                session:Annotated[Session, Depends(get_session)]):
    user = authenticate_user (form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    expire_time = timedelta(minutes=EXPIRY_TIME)
    access_token = create_access_token({"sub":form_data.username}, expire_time)

    refresh_expire_time = timedelta(days=7)
    refresh_token = create_refresh_token({"sub":user.email}, refresh_expire_time)

    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)

@app.post("/token/refresh")
def refresh_token(old_refresh_token:str,
                  session:Annotated[Session, Depends(get_session)]):
    
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token, Please login again",
        headers={"www-Authenticate":"Bearer"}
    )
    
    user = validate_refresh_token(old_refresh_token,
                                  session)
    if not user:
        raise credential_exception
    
    expire_time = timedelta(minutes=EXPIRY_TIME)
    access_token = create_access_token({"sub":user.username}, expire_time)

    refresh_expire_time = timedelta(days=7)
    refresh_token = create_refresh_token({"sub":user.email}, refresh_expire_time)

    return Token(access_token=access_token, token_type= "bearer", refresh_token=refresh_token)












