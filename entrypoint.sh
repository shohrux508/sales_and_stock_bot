#!/bin/bash

# Остановка скрипта при ошибке
set -e

# Убеждаемся, что мы в директории /app
cd /app

echo "Current directory: $(pwd)"
echo "Listing migrations..."
ls -R migrations/versions/

echo "Applying database migrations..."
# Используем прямой вызов alembic
alembic upgrade head

echo "Starting Application..."
python main.py
