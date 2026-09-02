import os

os.environ["INVENTORY_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["INVENTORY_APP_ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def product_payload():
    return {
        "sku": "PROD-001",
        "name": "Producto de prueba",
        "description": "Artículo usado por la suite de pruebas.",
        "category": "Pruebas",
        "unit": "unidad",
        "minimum_stock": 10,
        "is_active": True,
    }


def create_product(client, sku="PROD-001", minimum_stock=10):
    response = client.post(
        "/api/products",
        json={
            "sku": sku,
            "name": f"Producto {sku}",
            "category": "Pruebas",
            "unit": "unidad",
            "minimum_stock": minimum_stock,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_location(client, name="Depósito de prueba"):
    response = client.post(
        "/api/locations",
        json={"name": name, "description": "Ubicación para pruebas", "is_active": True},
    )
    assert response.status_code == 201
    return response.json()


def create_entry(client, product_id, location_id, amount):
    return client.post(
        "/api/movements",
        json={
            "movement_type": "ENTRY",
            "product_id": product_id,
            "quantity": amount,
            "destination_location_id": location_id,
            "notes": "Entrada de prueba",
        },
    )
