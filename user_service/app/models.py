from fastapi import Form
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Annotated

class User (SQLModel, table=True):
        id: int = Field(default=None, primary_key=True)
        username: str
        email:str
        password:str

class Register_User (BaseModel):
            username: Annotated[
            str,
            Form(),
        ]
            email: Annotated[
            str,
            Form(),
        ]
            password: Annotated[
            str,
            Form(),
        ]

class Token (BaseModel):
        access_token:str
        token_type: str

class TokenData (BaseModel):
        username:str


class Todo_Create (BaseModel):
    content: str

class Todo_Edit (BaseModel):
       content:str
       is_completed: bool




