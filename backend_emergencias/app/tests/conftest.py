from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import decode_token, hash_password
from app.main import app
from app.modules.incidentes_servicios import models as _incidentes_models  # noqa: F401 — metadata
from app.modules.sistema.models import Bitacora, TokenRevocado  # noqa: F401 — metadata
from app.modules.taller_tecnico import models as _taller_tecnico_models  # noqa: F401 — metadata
from app.modules.usuario_autenticacion.models import Rol, Usuario, usuario_rol


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
        seed.flush()
        seed.execute(
            usuario_rol.insert().values(id_usuario=user.id, id_rol=rol.id),
        )
        seed.execute(
            usuario_rol.insert().values(id_usuario=user_cliente.id, id_rol=rol_cliente.id),
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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        delattr(app.state, "test_engine")
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
