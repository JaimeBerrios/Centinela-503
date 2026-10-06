import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"

def test_unauthorized_access():
    response = client.get("/api/operations/incidents")
    assert response.status_code == 401
    
    response = client.post("/api/sensors/clear-hardware")
    assert response.status_code == 401
