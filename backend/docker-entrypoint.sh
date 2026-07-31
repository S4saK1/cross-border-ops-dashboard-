#!/bin/sh
set -e

echo "[entrypoint] Initializing database (importing term dictionary)..."
python -m alembic upgrade head && python init_db.py --skip-create-tables

if [ "$ENVIRONMENT" = "production" ]; then
    echo "[entrypoint] Starting uvicorn in PRODUCTION mode (workers=4)..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    echo "[entrypoint] Starting uvicorn in DEVELOPMENT mode (reload)..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
