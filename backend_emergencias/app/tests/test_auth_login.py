from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.main import app
from app.modules.sistema.bitacora_service import AUDIT_ACTION_LOGIN, AUDIT_ACTION_LOGOUT, AUDIT_MODULE_USER_AUTH
from app.modules.sistema.models import Bitacora, TokenRevocado
from app.modules.usuario_autenticacion.models import Usuario


def test_login_ok_returns_bearer_token_and_roles(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert "Administrador" in body["roles"]
    assert body["redirect_hint"] == "web"

    payload = decode_token(body["access_token"])
    assert payload["sub"] is not None
    assert payload["type"] == "access"
    assert "Administrador" in payload["roles"]
    assert payload.get("jti")


def test_login_wrong_password_401(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "mala-clave"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Credenciales inválidas"


def test_login_ok_persists_bitacora_row(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert res.status_code == 200
    engine = app.state.test_engine
    with Session(engine) as db:
        uid = db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()
        rows = db.execute(
            select(Bitacora).where(
                Bitacora.id_usuario == uid,
                Bitacora.modulo == AUDIT_MODULE_USER_AUTH,
                Bitacora.accion == AUDIT_ACTION_LOGIN,
                Bitacora.resultado == "OK",
            ),
        ).scalars().all()
        assert len(rows) >= 1


def test_login_wrong_password_persists_failed_audit(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "mala-clave"},
    )
    assert res.status_code == 401
    engine = app.state.test_engine
    with Session(engine) as db:
        uid = db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()
        rows = db.execute(
            select(Bitacora).where(
                Bitacora.id_usuario == uid,
                Bitacora.accion == AUDIT_ACTION_LOGIN,
                Bitacora.resultado == "FALLO_CREDENCIAL",
            ),
        ).scalars().all()
        assert len(rows) >= 1


def test_logout_persists_bitacora_and_revokes_jti(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    jti = decode_token(token)["jti"]
    out = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.status_code == 204

    engine = app.state.test_engine
    with Session(engine) as db:
        uid = db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()
        assert db.get(TokenRevocado, jti) is not None
        rows = db.execute(
            select(Bitacora).where(
                Bitacora.id_usuario == uid,
                Bitacora.modulo == AUDIT_MODULE_USER_AUTH,
                Bitacora.accion == AUDIT_ACTION_LOGOUT,
                Bitacora.resultado == "OK",
            ),
        ).scalars().all()
        assert len(rows) >= 1
