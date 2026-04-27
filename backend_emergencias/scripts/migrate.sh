#!/usr/bin/env sh
# Ejecutar desde la raíz del servicio: directorio que contiene `alembic.ini` (backend_emergencias).
# Render (Linux): en Start Command, p.ej. `sh scripts/migrate.sh && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
set -e
cd "$(dirname "$0")/.."
exec alembic upgrade head
