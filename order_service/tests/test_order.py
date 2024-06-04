import pytest
from httpx import AsyncClient
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient
from main import app, get_session
from models.order import Order

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

def test_create_order(client: TestClient):
    response = client.post("/orders/", json={"user_id": 1, "product_id": 1, "quantity": 2, "total_price": 20.0})
    assert response.status_code == 201
    assert response.json()["user_id"] == 1
    assert response.json()["product_id"] == 1

def test_read_order(client: TestClient):
    response = client.post("/orders/", json={"user_id": 1, "product_id": 1, "quantity": 2, "total_price": 20.0})
    order_id = response.json()["id"]
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["id"] == order_id
