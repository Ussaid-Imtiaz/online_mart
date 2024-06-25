from typing import Annotated
from fastapi import Depends
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from .. import models, settings

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
def create_tables() -> None:
    SQLModel.metadata.create_all(engine)
    

def get_session():
    with Session(engine) as session:        
        yield session   
        
async def create_user(session: Annotated[Session, Depends(get_session)], username: str, email: str, hashed_password: str):
        user = models.User(username=username, email=email, hashed_password=hashed_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

async def get_user_by_username(session: Annotated[Session, Depends(get_session)], username: str):
        result = session.exec(select(models.User).where(models.User.username == username))
        return result.first()



