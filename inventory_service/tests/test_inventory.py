import pytest
from httpx import AsyncClient
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient
from main import app, get_session
from models.inventory import Inventory

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

@pytest.mark.asyncio
async def test_create_inventory(client: AsyncClient):
    response = await client.post("/inventory/", json={"product_id": 1, "quantity": 100})
    assert response.status_code == 201
    assert response.json()["product_id"] == 1
    assert response.json()["quantity"] == 100

@pytest.mark.asyncio
async def test_read_inventory(client: AsyncClient):
    response = await client.post("/inventory/", json={"product_id": 1, "quantity": 100})
    inventory_id = response.json()["id"]
    response = await client.get(f"/inventory/{inventory_id}")
    assert response.status_code == 200
    assert response.json()["id"] == inventory_id
