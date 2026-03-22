#!/bin/bash

# Остановка скрипта при ошибке
set -e

echo "Applying database migrations..."
python -m alembic upgrade head

echo "Starting Application..."
python main.py
