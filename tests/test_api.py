import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.api.server import create_app
from app.container import Container
from app.services.transaction_service import TransactionService
from app.services.product_service import ProductService
from app.services.category_service import CategoryService
from app.config import settings
import base64

@pytest_asyncio.fixture
async def app_client(async_session_maker):
    container = Container()
    container.register("transaction_service", TransactionService(async_session_maker))
    container.register("product_service", ProductService(async_session_maker))
    container.register("category_service", CategoryService(async_session_maker))
    
    app = create_app(container)
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

def get_auth_headers(username, password):
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

@pytest.mark.asyncio
async def test_dashboard_auth_fail(app_client: AsyncClient):
    response = await app_client.get("/")
    assert response.status_code == 401
    
    response = await app_client.get("/api/stats")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_dashboard_auth_success(app_client: AsyncClient):
    headers = get_auth_headers("admin", settings.DASHBOARD_PASSWORD)
    
    response = await app_client.get("/", headers=headers)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
@pytest.mark.asyncio
async def test_api_inventory(app_client: AsyncClient):
    headers = get_auth_headers("admin", settings.DASHBOARD_PASSWORD)
    response = await app_client.get("/api/inventory", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    # We seeded one product in conftest.py
    assert len(data["inventory"]) == 1
    assert data["inventory"][0]["name"] == "Test Product"

@pytest.mark.asyncio
async def test_api_stats(app_client: AsyncClient):
    headers = get_auth_headers("admin", settings.DASHBOARD_PASSWORD)
    response = await app_client.get("/api/stats?period=week", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 0
    assert data["total_revenue"] == 0
    assert "products_breakdown" in data
