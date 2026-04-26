from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import decode_token, hash_password
from app.main import app
from app.modules.incidentes_servicios import models as _incidentes_models  # noqa: F401 — metadata
from app.modules.pagos import models as _pagos_models  # noqa: F401 — metadata
from app.modules.sistema.models import Bitacora, IdempotenciaRegistro, TokenRevocado  # noqa: F401 — metadata
from app.modules.taller_tecnico import models as _taller_tecnico_models  # noqa: F401 — metadata
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Rol, Usuario, usuario_rol


@pytest.fixture(autouse=True)
def _disable_external_google_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not call Gemini with keys from `.env`; pipeline uses fallback determinístico."""
    monkeypatch.setattr(settings, "google_ai_api_key", "", raising=False)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    seed = TestingSessionLocal()
    try:
        rol = Rol(id=1, nombre="Administrador", descripcion="Test")
        seed.add(rol)
        rol_cliente = Rol(nombre="Cliente", descripcion="Test")
        seed.add(rol_cliente)
        rol_tecnico = Rol(nombre="Tecnico", descripcion="Mecánico")
        seed.add(rol_tecnico)
        user = Usuario(
            nombre="Test",
            apellido="Usuario",
            email="login-test@example.com",
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        seed.add(user)
        user_cliente = Usuario(
            nombre="Cliente",
            apellido="Web",
            email="cliente-test@example.com",
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        seed.add(user_cliente)
        user_tecnico = Usuario(
            nombre="Técnico",
            apellido="Test",
            email="tecnico-test@example.com",
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        seed.add(user_tecnico)
        seed.flush()
        seed.execute(
            usuario_rol.insert().values(id_usuario=user.id, id_rol=rol.id),
        )
        seed.execute(
            usuario_rol.insert().values(id_usuario=user_cliente.id, id_rol=rol_cliente.id),
        )
        seed.execute(
            usuario_rol.insert().values(id_usuario=user_tecnico.id, id_rol=rol_tecnico.id),
        )
        taller = Taller(
            id_admin=user.id,
            nombre="Taller Test",
            direccion="Dir test 123",
            latitud=-34.6037,
            longitud=-58.3816,
            disponibilidad=True,
            capacidad_max=5,
            calificacion=0,
        )
        seed.add(taller)
        seed.flush()
        seed.add(
            MecanicoTaller(
                id_usuario=user_tecnico.id,
                id_taller=taller.id,
                especialidad="motor",
            ),
        )
        seed.commit()
    finally:
        seed.close()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Tests de vehículos/incidentes: misma BD en memoria para insertar filas auxiliares
    app.state.test_engine = engine
    # BackgroundTasks deben abrir sesión sobre el mismo engine que `get_db` (no `SessionLocal` prod).
    app.state.background_sessionmaker = TestingSessionLocal
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        delattr(app.state, "test_engine")
        delattr(app.state, "background_sessionmaker")
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
