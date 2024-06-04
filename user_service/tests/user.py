import pytest
from httpx import AsyncClient
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient
from main import app, get_session
from models.user import User
from hashing import hash_password

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, echo=True)

# Create a test database session
def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture
async def client():
    SQLModel.metadata.create_all(engine)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    SQLModel.metadata.drop_all(engine)

def test_create_user(client):
    response = client.post("/users/", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"

def test_login(client):
    # First, create a user
    hashed_password = hash_password("password123")
    user = User(username="testuser", email="test@example.com", hashed_password=hashed_password)
    with Session(engine) as session:
        session.add(user)
        session.commit()

    # Now, test login
    response = client.post("/users/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
