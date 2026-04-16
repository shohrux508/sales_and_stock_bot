#!/bin/bash

# Do NOT use set -e — migration failures should not block startup
cd /app

echo "Current directory: $(pwd)"
echo "Listing migrations..."
ls -R migrations/versions/

echo "Applying database migrations (timeout: 30s)..."
if timeout 30 alembic upgrade head; then
    echo "Migrations applied successfully."
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "WARNING: Migration timed out after 30 seconds. Starting app anyway..."
    else
        echo "WARNING: Migration failed with exit code $EXIT_CODE. Starting app anyway..."
    fi
fi

echo "Starting Application..."
exec python main.py
