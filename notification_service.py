import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import aio_pika
import asyncio
import json
from pathlib import Path

app = FastAPI()

# Настройки RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@rabbitmq/"
QUEUE_NAME = "notifications"

# Файл для хранения уведомлений
NOTIFICATIONS_FILE = Path("notifications.json")

# Список активных WebSocket-подключений
active_connections = []

# Инициализация файла
if not NOTIFICATIONS_FILE.exists():
    NOTIFICATIONS_FILE.write_text("[]")


async def consume_notifications():
    """Потребляет уведомления из RabbitMQ и сохраняет их в файл."""
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        print(" [*] Ожидание уведомлений из RabbitMQ.")

        async for message in queue:
            async with message.process():
                try:
                    notification_data = json.loads(message.body)

                    # Сохраняем уведомление в файл
                    current_notifications = json.loads(NOTIFICATIONS_FILE.read_text())
                    current_notifications.append(notification_data)
                    NOTIFICATIONS_FILE.write_text(json.dumps(current_notifications, indent=4))

                    # Отправляем уведомление активным WebSocket-клиентам
                    for connection in active_connections:
                        await connection.send_text(json.dumps(notification_data))
                except Exception as e:
                    print(f"Ошибка обработки сообщения: {e}")
    except Exception as e:
        print(f"Ошибка подключения к RabbitMQ: {e}")


@app.on_event("startup")
async def startup():
    """Запускает задачу потребления уведомлений при старте приложения."""
    asyncio.create_task(consume_notifications())


@app.get("/notifications")
async def get_notifications():
    """Возвращает список уведомлений из файла."""
    return json.loads(NOTIFICATIONS_FILE.read_text())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Обрабатывает WebSocket подключения."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(3600)  # Поддерживаем соединение активным
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("Клиент отключился")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8002)
