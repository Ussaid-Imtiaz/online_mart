from sqlmodel import SQLModel, create_engine, Session
from app import setting


# Step-1: Create Database on Neon
# Step-2: Create .env file for environment variables
# Step-3: Create setting.py file for encrypting DatabaseURL

# Create a variable using url as parameter and add psycopg with postgresql in url.
connection_string: str = str(   # Convert URL into string
    setting.DATABASE_URL
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
