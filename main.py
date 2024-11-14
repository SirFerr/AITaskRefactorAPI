from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
import uuid
import os
import json
import requests
import uvicorn

app = FastAPI()

# URL и заголовки для использования Qwen модели
API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct"
HEADERS = {"Authorization": "Bearer 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"}

# Файлы для хранения ID запросов и запросов генерации
REQUEST_IDS_FILE = "request_ids.json"
GENERATION_REQUESTS_FILE = "generation_requests.json"


# Функция для загрузки ID запросов из файла
def load_request_ids():
    if os.path.exists(REQUEST_IDS_FILE):
        with open(REQUEST_IDS_FILE, "r") as file:
            return json.load(file)
    return []


# Функция для сохранения ID запросов в файл
def save_request_ids(request_ids):
    with open(REQUEST_IDS_FILE, "w") as file:
        json.dump(request_ids, file)


# Функция для загрузки запросов генерации из файла
def load_generation_requests():
    if os.path.exists(GENERATION_REQUESTS_FILE):
        with open(GENERATION_REQUESTS_FILE, "r") as file:
            return json.load(file)
    return {}


# Функция для сохранения запросов генерации в файл
def save_generation_requests():
    with open(GENERATION_REQUESTS_FILE, "w") as file:
        json.dump(generation_requests, file)


# Инициализация ID запросов и запросов генерации
request_ids = load_request_ids()
generation_requests = load_generation_requests()

DEFAULT_PROMPT = "Сделай задачу более четкой и выдели явные подзадачи."


class TextRequest(BaseModel):
    text: str
    max_tokens: int = 100


@app.get("/")
def read_root():
    return {"message": "Hello World"}


# Ручка для создания запроса на генерацию текста
@app.post("/generate/request")
async def request_text_generation(request: TextRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())

    generation_requests[request_id] = {
        "prompt": DEFAULT_PROMPT,
        "user_text": request.text,
        "max_tokens": request.max_tokens,
        "status": "in_progress",
        "generated_text": None
    }

    # Добавляем request_id в список и сохраняем его
    request_ids.append(request_id)
    save_request_ids(request_ids)
    save_generation_requests()  # Сохранение обновленного словаря generation_requests

    # Запуск генерации текста в фоне
    background_tasks.add_task(generate_text, request_id)

    return {"request_id": request_id}


def generate_text(request_id: str):
    request_data = generation_requests.get(request_id)
    if not request_data:
        return

    try:
        # Запрос к API Hugging Face
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={
                "inputs": f"{request_data['prompt']} {request_data['user_text']}",
                "parameters": {"max_length": request_data["max_tokens"]}
            }
        )
        result = response.json()

        # Проверка, является ли результат списком, и выбор первого элемента, если это так
        if isinstance(result, list):
            result = result[0]

        # Сохранение сгенерированного текста
        request_data["generated_text"] = result.get("generated_text", "Ошибка при генерации текста")
        request_data["status"] = "completed"
    except Exception as e:
        request_data["status"] = "failed"
        request_data["error"] = str(e)

    # Сохранение обновленного состояния


# Ручка для получения статуса генерации текста
@app.get("/generate/status")
async def get_generation_status(
        request_id: str = Query(..., description="Идентификатор запроса для получения статуса генерации.")
):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    return {"status": request_data["status"]}


# Ручка для предпросмотра сгенерированного текста
@app.get("/generate/preview")
async def preview_generated_text(
        request_id: str = Query(..., description="Идентификатор запроса для предпросмотра сгенерированного текста.")
):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if request_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Генерация текста еще не завершена")
    return {"preview_text": request_data["generated_text"]}


# Ручка для подтверждения или отмены генерации текста
@app.post("/generate/finalize")
async def finalize_generation(
        request_id: str = Query(..., description="Идентификатор запроса для финализации генерации текста."),
        apply: bool = Query(..., description="Флаг для подтверждения применения сгенерированного текста.")
):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if apply:
        return {"status": "Text generation applied", "final_text": request_data["generated_text"]}
    else:
        # Удаление запроса при отказе
        del generation_requests[request_id]
        request_ids.remove(request_id)
        save_request_ids(request_ids)
        save_generation_requests()  # Сохранение обновленного состояния после удаления запроса
        return {"status": "Text generation discarded", "final_text": None}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
