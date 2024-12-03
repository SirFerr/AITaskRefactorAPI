import pytest
from fastapi.testclient import TestClient
from main import app, SessionLocal, GenerationRequest

client = TestClient(app)

def setup_module():
    """Инициализация базы данных перед тестами."""
    db = SessionLocal()
    db.query(GenerationRequest).delete()
    db.commit()
    db.close()

def test_generate_request():
    response = client.post("/generate/request", json={"text": "Hello World", "max_tokens": 100})
    assert response.status_code == 200
    assert "request_id" in response.json()

def test_get_generation_status_not_found():
    response = client.get("/generate/status?request_id=nonexistent_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Запрос не найден"}

def test_generate_all_requests():
    response = client.get("/generate/all")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_preview_generated_text_incomplete():
    response = client.get("/generate/preview?request_id=nonexistent_id")
    assert response.status_code == 404

def test_finalize_generation_not_found():
    response = client.post("/generate/finalize", json={"request_id": "nonexistent_id", "apply": True})
    assert response.status_code == 404
