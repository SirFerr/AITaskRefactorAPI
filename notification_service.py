import uvicorn
from fastapi import FastAPI, BackgroundTasks
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

# Инициализация файла
if not NOTIFICATIONS_FILE.exists():
    NOTIFICATIONS_FILE.write_text("[]")

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consume_notifications():
    """Потребляет уведомления из RabbitMQ, сохраняет их в файл и выводит в консоль."""
    print("Потребитель запущен...")
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await connection.channel()
            queue = await channel.declare_queue(QUEUE_NAME, durable=True)

            logger.info(" [*] Ожидание уведомлений из RabbitMQ.")

            async for message in queue:
                async with message.process():
                    try:
                        logger.info("Сообщение получено!")

                        notification_data = json.loads(message.body)

                        # Сохраняем уведомление в файл
                        current_notifications = json.loads(NOTIFICATIONS_FILE.read_text())
                        current_notifications.append(notification_data)
                        NOTIFICATIONS_FILE.write_text(json.dumps(current_notifications, indent=4))

                        logger.info(f"Получено уведомление: {notification_data}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки сообщения: {e}")
        except Exception as e:
            print(f"Ошибка подключения к RabbitMQ: {e}. Повторная попытка через 5 секунд...")
            await asyncio.sleep(5)





@app.on_event("startup")
async def startup():
    try:
        logger.info("Приложение запускается...")
        # Запускаем consume_notifications как фоновую задачу
        asyncio.create_task(consume_notifications())
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")



@app.get("/notifications")
async def get_notifications():
    """Возвращает список уведомлений из файла."""
    try:
        return json.loads(NOTIFICATIONS_FILE.read_text())
    except Exception as e:
        return {"error": f"Ошибка чтения уведомлений: {e}"}
