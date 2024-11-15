import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import aio_pika
import asyncio
import json
from fastapi.responses import HTMLResponse

app = FastAPI()

# Настройки RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@rabbitmq/"
QUEUE_NAME = "notifications"


# Модель уведомления
class Notification(BaseModel):
    event: str
    message: str


# Для передачи сообщений клиентам через WebSocket
active_connections = []

# Инициализация шаблонов Jinja2 для HTML
templates = Jinja2Templates(directory="templates")


async def consume_notifications():
    """Функция для получения уведомлений из RabbitMQ и отправки их через WebSocket."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    print(" [*] Ожидание уведомлений. Нажмите CTRL+C для выхода.")

    async for message in queue:
        async with message.process():
            try:
                notification_data = json.loads(message.body)
                notification = Notification(**notification_data)
                # Отправка уведомления всем активным WebSocket подключением в JSON формате
                for connection in active_connections:
                    await connection.send_text(json.dumps({
                        "event": notification.event,
                        "message": notification.message
                    }))
            except Exception as e:
                print(f"Ошибка обработки сообщения: {e}")


@app.on_event("startup")
async def startup():
    """Запускает задачу для потребления уведомлений при старте приложения."""
    asyncio.create_task(consume_notifications())


@app.get("/")
async def get(request: Request):
    """Отправка HTML страницы на фронтенд."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для динамической передачи уведомлений на страницу."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Держим подключение открытым, ожидаем новых данных
            await asyncio.sleep(3600)  # Просто пустая задержка, поддерживающая WebSocket активным
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("Client disconnected")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8002)
