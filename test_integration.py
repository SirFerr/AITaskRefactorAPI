import pytest
from aio_pika import connect_robust, Message
import asyncio
from NotiService.notification_service import NOTIFICATIONS_FILE

RABBITMQ_URL = "amqp://guest:guest@localhost/"
QUEUE_NAME = "notifications"

@pytest.mark.asyncio
async def test_rabbitmq_integration():
    """Проверка взаимодействия RabbitMQ между сервисами."""
    connection = await connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    # Отправка сообщения в RabbitMQ
    await channel.default_exchange.publish(
        Message(b'{"event": "TestEvent", "message": "TestMessage"}'),
        routing_key=QUEUE_NAME,
    )

    await asyncio.sleep(2)  # Ожидание обработки сообщения

    # Проверка файла уведомлений
    notifications = NOTIFICATIONS_FILE.read_text()
    assert "TestEvent" in notifications
    assert "TestMessage" in notifications

    await connection.close()
