import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger(__name__)


def _run_alembic_upgrade_head() -> None:
    """Ejecuta migraciones contra `settings.database_url` (misma URL que el engine)."""
    from alembic import command
    from alembic.config import Config

    backend_root = Path(__file__).resolve().parents[1]
    ini_path = backend_root / "alembic.ini"
    if not ini_path.is_file():
        logger.warning("alembic.ini no encontrado en %s; omitiendo migraciones", ini_path)
        return
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if settings.run_db_migrations_on_startup:
        try:
            await asyncio.to_thread(_run_alembic_upgrade_head)
            logger.info("Migraciones DB: alembic upgrade head OK")
        except Exception:
            logger.exception("Migraciones DB fallaron al arranque")
            raise
    yield


from app.modules.incidentes_servicios.ai_analysis_router import router as ia_analysis_router
from app.modules.incidentes_servicios.calificaciones_router import admin_router as admin_calificaciones_router
from app.modules.incidentes_servicios.calificaciones_router import router as calificaciones_router
from app.modules.incidentes_servicios.router import router as incidentes_router
from app.modules.pagos.router import router as pagos_router
from app.modules.sistema.notificaciones_api import notificaciones_router
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

app = FastAPI(title="Emergencias API", version="0.1.0", lifespan=_lifespan)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(vehiculos_router, prefix="/api")
app.include_router(sistema_router, prefix="/api")
app.include_router(notificaciones_router, prefix="/api/sistema")
app.include_router(bitacora_router, prefix="/api")
app.include_router(taller_router, prefix="/api")
app.include_router(admin_talleres_router, prefix="/api")
app.include_router(incidentes_router, prefix="/api")
app.include_router(ia_analysis_router, prefix="/api")
app.include_router(calificaciones_router, prefix="/api")
app.include_router(admin_calificaciones_router, prefix="/api")
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
    """Conexión a Postgres + diagnóstico de esquema (tabla `calificacion`, revisión Alembic)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            cal_exists = bool(
                conn.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = 'calificacion')"
                    )
                ).scalar()
            )
            alembic_rev: str | None = None
            try:
                alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
            except Exception:
                alembic_rev = None
        return {
            "database": "connected",
            "calificacion_table_exists": cal_exists,
            "alembic_version": alembic_rev,
            "run_db_migrations_on_startup": settings.run_db_migrations_on_startup,
        }
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"database": "error", "detail": str(exc)},
        )
