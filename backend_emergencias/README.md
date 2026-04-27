# Backend emergencias (FastAPI)

## Estructura

- `app/main.py` — entrada FastAPI.
- `app/core/` — configuración, BD, seguridad (JWT, bcrypt).
- `app/modules/` — cinco paquetes de dominio (UML): `usuario_autenticacion`, `taller_tecnico`, `incidentes_servicios`, `pagos`, `sistema`.
- `app/tests/` — pruebas unitarias (pendiente).

## Arranque

```powershell
cd backend_emergencias
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: `http://127.0.0.1:8000/docs`.

## Migraciones (Alembic)

Tras `pip install -r requirements.txt`, aplicá los cambios de esquema en PostgreSQL (usa la misma URL que `.env` → `database_url`):

```powershell
cd backend_emergencias
.\venv\Scripts\activate
alembic upgrade head
```

### Producción (Render, Neon, etc.)

1. **Variable de entorno:** definí `DATABASE_URL` (o dejá la que inyecta Render con la base PostgreSQL; el backend normaliza `postgres://` / `postgresql://` a `postgresql+psycopg2://`).
2. **Aplicar migraciones** al menos una vez **antes** de que tráfico use la API, y en cada deploy **después** de un `git pull` que traiga archivos bajo `alembic/versions/`.

**Opción A – una sola vez por shell (o desde tu PC apuntando a la URL de producción):**

```powershell
cd backend_emergencias
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST:PORT/DBNAME"
alembic upgrade head
```

**Opción B – al arrancar el servicio en Render (recomendado):** en el servicio **Web** → *Settings* → *Start Command* (o el comando unificado de arranque), encadenar migración + uvicorn, por ejemplo:

```text
sh scripts/migrate.sh && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

(El *Root Directory* del build debe ser el que contiene `backend_emergencias` si el repo no es monorepo; si el root es `backend_emergencias`, el comando anterior es válido con `sh scripts/migrate.sh`.)

3. Comprobar versión aplicada: en PostgreSQL, `SELECT * FROM alembic_version;` debería mostrar la cabeza (p. ej. `011_vehiculo_tiposeguro_fotofrontal`).

Faltan columnas o tablas (`ai_result_json`, `notificacion_push_token`, etc.) = **no se ejecutó** `alembic upgrade head` en esa base, o el deploy usó otra `DATABASE_URL`.

La primera revisión (`001_taller_cu06`) agrega `email` y `horario_atencion` a `taller` solo si faltan. Para nuevas revisiones:

```powershell
alembic revision -m "descripcion_corta"
```

(editá el archivo en `alembic/versions/` con `upgrade`/`downgrade`, luego `alembic upgrade head`).
