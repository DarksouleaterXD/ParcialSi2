from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import engine
from app.modules.incidentes_servicios.router import router as incidentes_router
from app.modules.pagos.router import router as pagos_router
from app.modules.sistema.router import router as sistema_router
from app.modules.taller_tecnico.router import admin_talleres_router, router as taller_router
from app.modules.usuario_autenticacion.router import auth_router, roles_router, users_router
from app.modules.usuario_autenticacion.vehiculos_router import vehiculos_router

# Registro de modelos SQLAlchemy (orden: tablas referenciadas por FK)
from app.modules.usuario_autenticacion import models as _usuario_models  # noqa: F401
from app.modules.incidentes_servicios import models as _incidentes_models  # noqa: F401
from app.modules.sistema import models as _sistema_models  # noqa: F401
from app.modules.taller_tecnico import models as _taller_models  # noqa: F401

app = FastAPI(title="Emergencias API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(vehiculos_router, prefix="/api")
app.include_router(sistema_router, prefix="/api")
app.include_router(taller_router, prefix="/api")
app.include_router(admin_talleres_router, prefix="/api")
app.include_router(incidentes_router, prefix="/api")
app.include_router(pagos_router, prefix="/api")


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
