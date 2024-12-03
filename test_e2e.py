import pytest
from fastapi.testclient import TestClient
from MainService.main import app as main_app
from NotiService.notification_service import app as notification_app, NOTIFICATIONS_FILE

main_client = TestClient(main_app)
notification_client = TestClient(notification_app)

def test_full_flow():
    """Тест полного взаимодействия между сервисами."""
    # Отправляем запрос на генерацию текста
    response = main_client.post("/generate/request", json={"text": "Hello World", "max_tokens": 100})
    assert response.status_code == 200
    request_id = response.json()["request_id"]

    # Проверяем статус генерации
    response = main_client.get(f"/generate/status?request_id={request_id}")
    assert response.status_code == 200

    # Проверяем, что уведомление было обработано NotificationService
    notifications = notification_client.get("/notifications")
    assert notifications.status_code == 200
    assert any("Request Created" in n["event"] for n in notifications.json())
