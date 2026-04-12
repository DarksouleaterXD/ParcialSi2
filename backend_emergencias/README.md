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
