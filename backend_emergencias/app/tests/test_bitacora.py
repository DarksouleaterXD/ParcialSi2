"""Tests de la API de consulta de bitácora (/api/admin/bitacora)."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Usuario


def _admin_bearer_without_login(client) -> str:
    """JWT de admin sin pasar por POST /login (evita filas extra de bitácora en asserts)."""
    engine = app.state.test_engine
    with Session(engine) as db:
        uid = db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()
    token, _, _ = create_access_token(subject=str(uid), roles=["Administrador"])
    return token


def _cliente_token(client) -> str:
    res = client.post(
        "/api/auth/login",
        json={"email": "cliente-test@example.com", "password": "clave-valida-123"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def _seed_bitacora() -> tuple[int, datetime]:
    engine = app.state.test_engine
    now = datetime.now().replace(microsecond=0)
    with Session(engine) as db:
        admin = db.execute(select(Usuario).where(Usuario.email == "login-test@example.com")).scalar_one()
        row = Bitacora(
            id_usuario=admin.id,
            modulo="usuario_autenticacion",
            accion="LOGIN",
            iporigen="127.0.0.1",
            resultado="OK",
            fechahora=now,
        )
        db.add(row)
        db.add(
            Bitacora(
                id_usuario=admin.id,
                modulo="usuario_autenticacion",
                accion="ROLE_UPDATE",
                iporigen="127.0.0.1",
                resultado="OK",
                fechahora=now - timedelta(days=1),
            ),
        )
        db.commit()
        db.refresh(row)
        return row.id, now


def test_bitacora_list_admin_with_filters(client):
    bitacora_id, now = _seed_bitacora()
    token = _admin_bearer_without_login(client)

    res = client.get(
        "/api/admin/bitacora",
        params={
            "page": 1,
            "page_size": 10,
            "modulo": "usuario_autenticacion",
            "accion": "LOGIN",
            "usuario": "login-test@example.com",
            "fecha": now.date().isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == bitacora_id
    assert body["items"][0]["usuario"]["email"] == "login-test@example.com"


def test_bitacora_detail_admin_ok(client):
    bitacora_id, _ = _seed_bitacora()
    token = _admin_bearer_without_login(client)

    res = client.get(
        f"/api/admin/bitacora/{bitacora_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == bitacora_id
    assert body["modulo"] == "usuario_autenticacion"
    assert body["accion"] == "LOGIN"


def test_bitacora_requires_admin_role(client):
    token = _cliente_token(client)
    res = client.get(
        "/api/admin/bitacora",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
