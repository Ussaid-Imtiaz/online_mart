from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/imtiaz_mart"

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

async def init_db():
    SQLModel.metadata.create_all(engine)
