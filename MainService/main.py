import uuid
import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from huggingface_hub import InferenceClient
import aio_pika
import asyncio

# Настройки базы данных PostgreSQL
DATABASE_URL = "postgresql://admin:admin@db:5432/generation_db"

# Настройки SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель таблицы для хранения запросов на генерацию текста
class GenerationRequest(Base):
    __tablename__ = "generation_requests"

    id = Column(String, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    user_text = Column(Text, nullable=False)
    generated_text = Column(Text, nullable=True)
    status = Column(String, default="in_progress")

# Инициализация базы данных
Base.metadata.create_all(bind=engine)

# Инициализация клиента Hugging Face
client = InferenceClient(api_key="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")

# Инициализация FastAPI приложения
app = FastAPI()

# Настройки RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@rabbitmq/"

async def send_notification(event: str, message: str):
    """Отправка уведомлений в RabbitMQ."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=f'{{"event": "{event}", "message": "{message}"}}'.encode()),
            routing_key="notifications"
        )

# Значение по умолчанию для промта
DEFAULT_PROMPT = """Переформулируй задачу более четко, следуя этим правилам:
1. Опиши основную цель задачи кратко и ясно.
2. Разбей задачу на несколько логически связанных подзадач, чтобы они могли выполняться последовательно.
3. Каждая подзадача должна содержать конкретные шаги для выполнения.
4. Не повторяй исходную задачу, а переформулируй ее для большей ясности."""

# Модель для запроса на генерацию текста
class TextRequest(BaseModel):
    text: str
    max_tokens: int = 10000


@app.post("/generate/request")
async def request_text_generation(request: TextRequest, background_tasks: BackgroundTasks):
    """Создание нового запроса на генерацию текста."""
    request_id = str(uuid.uuid4())

    # Сохранение запроса в базу данных
    db = SessionLocal()
    new_request = GenerationRequest(
        id=request_id,
        user_text=request.text,
        status="in_progress"
    )
    db.add(new_request)
    db.commit()
    db.close()

    # Отправка уведомления о создании нового запроса
    await send_notification("Request Created", f"Request {request_id} has been created.")

    # Запуск задачи генерации текста в фоне
    background_tasks.add_task(generate_text, request_id)
    return {"request_id": request_id}


async def generate_text(request_id: str):
    """Фоновая задача для генерации текста."""
    db = SessionLocal()
    request_data = db.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()
    if not request_data:
        return

    try:
        # Разделение на промт и пользовательский текст
        prompt = DEFAULT_PROMPT
        user_input = request_data.user_text

        # Формирование сообщений
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input}
        ]

        # Запрос к Hugging Face для генерации текста с потоковой передачей
        stream = client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            max_tokens=10000,
            stream=True
        )

        generated_text = ""
        for chunk in stream:
            generated_text += chunk.choices[0].delta.content

        # Сохранение результата
        request_data.generated_text = generated_text
        request_data.status = "completed"
        await send_notification("Request Completed", f"Request {request_id} has been completed.")
    except Exception as e:
        request_data.status = "failed"
        await send_notification("Request Failed", f"Request {request_id} failed with error: {e}")
    finally:
        db.commit()
        db.close()


@app.get("/generate/status")
async def get_generation_status(request_id: str):
    """Получение статуса генерации текста."""
    db = SessionLocal()
    request_data = db.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()
    db.close()

    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    # Отправка уведомления о проверке статуса
    await send_notification("Status Checked", f"Status of request {request_id} was checked.")

    return {"status": request_data.status}


@app.get("/generate/preview")
async def preview_generated_text(request_id: str):
    """Получение предварительного результата генерации текста."""
    db = SessionLocal()
    request_data = db.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()
    db.close()

    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if request_data.status != "completed":
        raise HTTPException(status_code=400, detail="Генерация текста еще не завершена")

    # Отправка уведомления о просмотре результата
    await send_notification("Preview Accessed", f"Preview of request {request_id} was accessed.")

    return {"preview_text": request_data.generated_text}


@app.post("/generate/finalize")
async def finalize_generation(request_id: str, apply: bool):
    """Подтверждение или отмена сгенерированного текста."""
    db = SessionLocal()
    request_data = db.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()

    if not request_data:
        db.close()
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if apply:
        request_data.status = "approved"
        await send_notification("Request Approved", f"Request {request_id} has been approved.")
    else:
        request_data.status = "rejected"
        await send_notification("Request Rejected", f"Request {request_id} has been rejected.")

    db.commit()
    db.close()
    return {"status": f"Text generation {'applied' if apply else 'discarded'}"}


@app.get("/generate/all")
async def get_all_requests():
    """Получение всех запросов из базы данных."""
    db = SessionLocal()
    requests = db.query(GenerationRequest).all()
    db.close()

    # Отправка уведомления о запросе всех данных
    await send_notification("All Requests Accessed", "All generation requests have been accessed.")

    return [
        {
            "id": request.id,
            "date": request.date,
            "user_text": request.user_text,
            "generated_text": request.generated_text,
            "status": request.status
        }
        for request in requests
    ]


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
