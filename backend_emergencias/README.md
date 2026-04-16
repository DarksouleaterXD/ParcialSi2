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

La primera revisión (`001_taller_cu06`) agrega `email` y `horario_atencion` a `taller` solo si faltan. Para nuevas revisiones:

```powershell
alembic revision -m "descripcion_corta"
```

(editá el archivo en `alembic/versions/` con `upgrade`/`downgrade`, luego `alembic upgrade head`).
