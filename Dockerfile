# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для сборки (если потребуются)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Делаем entrypoint скрипт исполняемым
RUN chmod +x entrypoint.sh

# Открываем порт для FastAPI
EXPOSE 8000

# Используем CMD для запуска миграций и приложения
CMD ["/app/entrypoint.sh"]
