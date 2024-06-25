from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlmodel import Session
from app.db.crud import get_session, get_user_by_username

# Dependency
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key to sign JWT tokens (replace with a secure random key in production)
SECRET_KEY = "mysecretkey"

# Token expiration time (e.g., 15 minutes for testing purposes)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(session: Annotated[Session, Depends(get_session)], username: str, password: str):
    user = await get_user_by_username(session, username)
    if not user or not pwd_context.verify(password, user.hashed_password):
        return None
    return user

async def get_current_user(session: Annotated[Session, Depends(get_session)],token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_username(session, username)
    if user is None:
        raise credentials_exception

    return user


