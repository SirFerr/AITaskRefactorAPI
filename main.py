from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
import openai
import uuid

# uvicorn main:app --reload

from text import API_KEY  # Убедитесь, что ваш API-ключ хранится в этом файле

app = FastAPI()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Установите ваш API-ключ OpenAI
openai.api_key = API_KEY

# Хранилище для запросов на генерацию текста
generation_requests = {}

# Заранее заданный промт
DEFAULT_PROMPT = "Сделай задачу более четкой и выдели явные подзадачи."

# Модель для валидации данных запроса
class TextRequest(BaseModel):
    text: str
    max_tokens: int = 100



@app.get("/home")
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

    # Запускаем задачу генерации в фоне
    background_tasks.add_task(generate_text, request_id)

    return {"request_id": request_id}

# Функция для генерации текста в фоне
def generate_text(request_id: str):
    request_data = generation_requests.get(request_id)
    if not request_data:
        return

    try:
        # Генерация текста с использованием OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": request_data["prompt"]},
                {"role": "user", "content": request_data["user_text"]}
            ],
            max_tokens=request_data["max_tokens"],
            request_timeout=60
        )

        # Сохраняем сгенерированный текст
        request_data["generated_text"] = response['choices'][0]['message']['content'].strip()
        request_data["status"] = "completed"
    except Exception as e:
        request_data["status"] = "failed"
        request_data["error"] = str(e)

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
        # Удаляем запрос из памяти, если генерация отклонена
        del generation_requests[request_id]
        return {"status": "Text generation discarded", "final_text": None}
