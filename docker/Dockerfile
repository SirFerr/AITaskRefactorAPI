# Используем официальный образ Python
FROM python:3.12

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем все файлы из корневой директории проекта в контейнер
COPY ../ /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r /app/docker/requirements.txt

# Открываем порт для FastAPI приложения
EXPOSE 8001

# Команда для запуска приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
