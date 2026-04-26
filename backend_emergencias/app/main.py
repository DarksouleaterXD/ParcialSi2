from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.modules.incidentes_servicios.router import router as incidentes_router
from app.modules.pagos.router import router as pagos_router
from app.modules.sistema.router import bitacora_router, router as sistema_router
from app.modules.taller_tecnico.router import admin_talleres_router, router as taller_router
from app.modules.usuario_autenticacion.router import auth_router, roles_router, users_router
from app.modules.usuario_autenticacion.vehiculos_router import vehiculos_router

# Registro de modelos SQLAlchemy (orden: tablas referenciadas por FK)
from app.modules.usuario_autenticacion import models as _usuario_models  # noqa: F401
from app.modules.incidentes_servicios import models as _incidentes_models  # noqa: F401
from app.modules.pagos import models as _pagos_models  # noqa: F401
from app.modules.sistema import models as _sistema_models  # noqa: F401
from app.modules.taller_tecnico import models as _taller_models  # noqa: F401

app = FastAPI(title="Emergencias API", version="0.1.0")

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(vehiculos_router, prefix="/api")
app.include_router(sistema_router, prefix="/api")
app.include_router(bitacora_router, prefix="/api")
app.include_router(taller_router, prefix="/api")
app.include_router(admin_talleres_router, prefix="/api")
app.include_router(incidentes_router, prefix="/api")
app.include_router(pagos_router, prefix="/api")

# --- CORS: registrar este add_middleware al final del archivo ---
# Starlette inserta cada middleware al inicio de la pila; el último en registrarse queda más externo
# y atiende primero el preflight OPTIONS. Si agregás otro middleware, hacelo *arriba* de este bloque.
#
# Dev (CORS_ORIGINS vacío): orígenes explícitos (Angular + ejemplo Flutter web) + regex opcional
# para http(s)://localhost|127.0.0.1:* (Flutter web usa un puerto distinto en cada arranque).
#
# Prod: definir CORS_ORIGINS=https://tu-dominio.com,... (solo esa lista; no se aplica regex).
# Nunca uses "*" en allow_origins junto con allow_credentials=True.
_DEV_CORS_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:60578",
    "http://127.0.0.1:60578",
]
_LOCALHOST_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


def _cors_middleware_kwargs() -> dict:
    parsed = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if parsed:
        return {
            "allow_origins": parsed,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    base: dict = {
        "allow_origins": list(_DEV_CORS_ORIGINS),
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.cors_allow_localhost_regex:
        base["allow_origin_regex"] = _LOCALHOST_ORIGIN_REGEX
    return base


app.add_middleware(CORSMiddleware, **_cors_middleware_kwargs())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    """Comprueba que DATABASE_URL llega a PostgreSQL (SELECT 1)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"database": "error", "detail": str(exc)},
        )
