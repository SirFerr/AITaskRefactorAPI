from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import openai
import uuid

# uvicorn main:app --reload

from text import API_KEY

app = FastAPI()

# Установите ваш API-ключ OpenAI
openai.api_key = API_KEY

# Хранилище для запросов на генерацию текста
generation_requests = {}

# Заранее заданный промт
DEFAULT_PROMPT = "Сделай задачу более четкой и выдели явные подзадачи."

# Ручка для создания запроса на генерацию текста
@app.post("/generate/request")
async def request_text_generation(max_tokens: Optional[int] = Query(100, description="Максимальное количество токенов")):
    request_id = str(uuid.uuid4())
    generation_requests[request_id] = {
        "prompt": DEFAULT_PROMPT,
        "max_tokens": max_tokens,
        "status": "in_progress",
        "generated_text": None
    }
    # Инициируем генерацию текста асинхронно
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=DEFAULT_PROMPT,
        max_tokens=max_tokens
    )
    generation_requests[request_id]["generated_text"] = response.choices[0].text.strip()
    generation_requests[request_id]["status"] = "completed"
    return {"request_id": request_id}

# Ручка для получения статуса генерации текста
@app.get("/generate/status")
async def get_generation_status(request_id: str = Query(..., description="Идентификатор запроса")):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    return {"status": request_data["status"]}

# Ручка для предпросмотра сгенерированного текста
@app.get("/generate/preview")
async def preview_generated_text(request_id: str = Query(..., description="Идентификатор запроса")):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if request_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Генерация текста еще не завершена")
    return {"preview_text": request_data["generated_text"]}

# Ручка для подтверждения или отмены генерации текста
@app.post("/generate/finalize")
async def finalize_generation(request_id: str = Query(..., description="Идентификатор запроса"),
                              apply: bool = Query(..., description="Применить генерацию текста")):
    request_data = generation_requests.get(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if apply:
        return {"status": "Text generation applied", "final_text": request_data["generated_text"]}
    else:
        # Удаление запроса из памяти
        del generation_requests[request_id]
        return {"status": "Text generation discarded", "final_text": None}

