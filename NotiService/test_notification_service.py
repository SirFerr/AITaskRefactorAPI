import pytest
from fastapi.testclient import TestClient
from notification_service import app, NOTIFICATIONS_FILE

client = TestClient(app)

def setup_module():
    """Очистка файла уведомлений перед тестами."""
    NOTIFICATIONS_FILE.write_text("[]")

def test_get_notifications_empty():
    response = client.get("/notifications")
    assert response.status_code == 200
    assert response.json() == []

def test_get_notifications_with_data():
    """Симуляция добавления уведомлений."""
    NOTIFICATIONS_FILE.write_text('[{"event": "TestEvent", "message": "TestMessage"}]')
    response = client.get("/notifications")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["event"] == "TestEvent"
