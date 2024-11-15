import requests
import time

# Базовый URL для запросов
base_url = "http://localhost:8001/generate"

def generate_text(text, max_tokens=1000):
    # POST запрос для инициирования генерации текста
    response = requests.post(
        f"{base_url}/request",
        headers={"Content-Type": "application/json"},
        json={"text": text, "max_tokens": max_tokedns}
    )
    response_data = response.json()
    request_id = response_data.get("request_id")
    if request_id:
        print(f"Запрос успешно инициирован. ID запроса: {request_id}")
        return request_id
    else:
        print("Не удалось инициировать запрос.")
        return None

def check_status(request_id):
    # GET запрос для проверки статуса генерации
    response = requests.get(
        f"{base_url}/status?request_id={request_id}",
        headers={"Content-Type": "application/json"}
    )
    response_data = response.json()
    status = response_data.get("status")
    print(f"Статус: {status}")
    return status

def get_preview(request_id):
    # GET запрос для получения предпросмотра сгенерированного текста
    response = requests.get(
        f"{base_url}/preview?request_id={request_id}",
        headers={"Content-Type": "application/json"}
    )
    response_data = response.json()
    return response_data.get("preview_text")

def finalize_generation(request_id, apply=True):
    # POST запрос для подтверждения и применения сгенерированного текста
    response = requests.post(
        f"{base_url}/finalize?request_id={request_id}&apply={str(apply).lower()}",
        headers={"Content-Type": "application/json"},
        json={}
    )
    response_data = response.json()
    return response_data

def main():
    # Текст для генерации и настройки max_tokens
    text_to_generate = "нужно создать клиент на kotlin с функционалом tinder  "

    # Шаг 1: Инициация запроса на генерацию текста
    request_id = generate_text(text_to_generate)
    if not request_id:
        return

    # Шаг 2: Проверка статуса до завершения или ошибки
    print("Ожидание завершения генерации...")
    while True:
        status = check_status(request_id)
        if status == "completed":
            print("Генерация завершена.")
            break
        elif status == "failed":
            print("Ошибка при генерации.")
            return
        else:
            print("Все еще генерируется... Ожидание 1 секунду перед повторной проверкой.")
            time.sleep(1)

    # Шаг 3: Получение предпросмотра
    preview = get_preview(request_id)
    if preview:
        print("Предпросмотр сгенерированного текста:", preview)
    else:
        print("Не удалось получить предпросмотр.")

    # Шаг 4: Подтверждение генерации
    finalize_response = finalize_generation(request_id)
    print("Ответ на подтверждение:", finalize_response)

if __name__ == "__main__":
    main()
