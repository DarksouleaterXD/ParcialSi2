"""Auditoría en bitácora para administración de usuarios y roles."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_ROLE_ASSIGN,
    AUDIT_ACTION_ROLE_DELETE,
    AUDIT_ACTION_ROLE_UNASSIGN,
    AUDIT_ACTION_USUARIO_CREAR,
    AUDIT_ACTION_USUARIO_DESACTIVAR,
    AUDIT_ACTION_USUARIO_EDITAR,
    AUDIT_MODULE_USER_AUTH,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Rol, Usuario
from sqlalchemy.orm import Session, selectinload


@pytest.fixture
def admin_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _admin_id() -> int:
    engine = app.state.test_engine
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        return db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()


def _count_bitacora(*, accion: str, resultado_contains: str | None = None) -> int:
    engine = app.state.test_engine
    from sqlalchemy.orm import Session

    admin_id = _admin_id()
    with Session(engine) as db:
        stmt = select(func.count()).select_from(Bitacora).where(
            Bitacora.id_usuario == admin_id,
            Bitacora.modulo == AUDIT_MODULE_USER_AUTH,
            Bitacora.accion == accion,
        )
        if resultado_contains:
            stmt = stmt.where(Bitacora.resultado.ilike(f"%{resultado_contains}%"))
        return int(db.execute(stmt).scalar_one())


def test_create_user_inserts_bitacora_row(client, admin_token: str) -> None:
    before = _count_bitacora(accion=AUDIT_ACTION_USUARIO_CREAR)
    r = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "email": "nuevo-audit@example.com",
            "id_rol": 1,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert r.status_code == 201
    after = _count_bitacora(accion=AUDIT_ACTION_USUARIO_CREAR)
    assert after == before + 1


def test_create_user_duplicate_email_bitacora(client, admin_token: str) -> None:
    before = _count_bitacora(accion=AUDIT_ACTION_USUARIO_CREAR, resultado_contains="EMAIL_DUPLICADO")
    r = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Otro",
            "apellido": "Nombre",
            "email": "login-test@example.com",
            "id_rol": 1,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert r.status_code == 409
    after = _count_bitacora(accion=AUDIT_ACTION_USUARIO_CREAR, resultado_contains="EMAIL_DUPLICADO")
    assert after == before + 1


def test_update_user_role_inserts_assign_unassign_rows(client, admin_token: str) -> None:
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Para",
            "apellido": "RolChange",
            "email": "rol-change-audit@example.com",
            "id_rol": 1,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    before_un = _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN)
    before_as = _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN)
    rol_cliente_id = 2
    up = client.patch(
        f"/api/admin/users/{uid}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"id_rol": rol_cliente_id},
    )
    assert up.status_code == 200
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN) == before_un + 1
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN) == before_as + 1


def test_deactivate_user_inserts_bitacora(client, admin_token: str) -> None:
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Baja",
            "apellido": "Logica",
            "email": "baja-audit@example.com",
            "id_rol": 2,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    before = _count_bitacora(accion=AUDIT_ACTION_USUARIO_DESACTIVAR)
    dl = client.delete(
        f"/api/admin/users/{uid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dl.status_code == 204
    after = _count_bitacora(accion=AUDIT_ACTION_USUARIO_DESACTIVAR)
    assert after == before + 1


def test_delete_role_in_use_blocked_and_audited(client, admin_token: str) -> None:
    rr = client.post(
        "/api/admin/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nombre": "RolTmpAudit", "descripcion": "x", "permisos": ["usuarios.ver"]},
    )
    assert rr.status_code == 201
    rid = rr.json()["id"]
    ur = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "User",
            "apellido": "ConRolTmp",
            "email": "user-roltmp@example.com",
            "id_rol": rid,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert ur.status_code == 201
    before = _count_bitacora(accion=AUDIT_ACTION_ROLE_DELETE, resultado_contains="EN_USO")
    dr = client.delete(
        f"/api/admin/roles/{rid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dr.status_code == 409
    after = _count_bitacora(accion=AUDIT_ACTION_ROLE_DELETE, resultado_contains="EN_USO")
    assert after == before + 1


def test_update_user_name_inserts_edit_row(client, admin_token: str) -> None:
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Edit",
            "apellido": "Nombre",
            "email": "edit-nombre-audit@example.com",
            "id_rol": 2,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    before = _count_bitacora(accion=AUDIT_ACTION_USUARIO_EDITAR)
    up = client.patch(
        f"/api/admin/users/{uid}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nombre": "Editado"},
    )
    assert up.status_code == 200
    after = _count_bitacora(accion=AUDIT_ACTION_USUARIO_EDITAR)
    assert after == before + 1


def test_create_user_writes_role_assign_audit(client, admin_token: str) -> None:
    before = _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN)
    r = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Assign",
            "apellido": "OnCreate",
            "email": "assign-on-create@example.com",
            "id_rol": 1,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert r.status_code == 201
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN) == before + 1


def test_roles_admin_only(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        json={"email": "cliente-test@example.com", "password": "clave-valida-123"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    gr = client.get("/api/admin/roles", headers={"Authorization": f"Bearer {token}"})
    assert gr.status_code == 403


def test_post_assign_user_role_endpoint(client, admin_token: str) -> None:
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Post",
            "apellido": "Assign",
            "email": "post-assign@example.com",
            "id_rol": 1,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    before_un = _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN)
    before_as = _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN)
    pa = client.post(
        f"/api/admin/users/{uid}/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"id_rol": 2},
    )
    assert pa.status_code == 200
    assert pa.json()["roles"] == ["Cliente"]
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN) == before_un + 1
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_ASSIGN) == before_as + 1


def test_unassign_last_role_rejected(client, admin_token: str) -> None:
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Solo",
            "apellido": "UnRol",
            "email": "solo-un-rol@example.com",
            "id_rol": 2,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    dr = client.delete(
        f"/api/admin/users/{uid}/roles/2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dr.status_code == 409


def _append_role(user_id: int, rol_id: int) -> None:
    engine = app.state.test_engine
    with Session(engine) as db:
        u = db.execute(
            select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id),
        ).scalar_one()
        r = db.get(Rol, rol_id)
        assert r is not None
        u.roles.append(r)
        db.commit()


def test_unassign_one_role_when_multiple(client, admin_token: str) -> None:
    rr = client.post(
        "/api/admin/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nombre": "RolExtraUnassign", "permisos": ["usuarios.ver"]},
    )
    assert rr.status_code == 201
    extra_rid = rr.json()["id"]
    cr = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Dos",
            "apellido": "Roles",
            "email": "dos-roles@example.com",
            "id_rol": 2,
            "password": "ClaveSegura9",
            "password_confirmacion": "ClaveSegura9",
        },
    )
    assert cr.status_code == 201
    uid = cr.json()["id"]
    _append_role(uid, extra_rid)
    before = _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN)
    dr = client.delete(
        f"/api/admin/users/{uid}/roles/2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dr.status_code == 204
    assert _count_bitacora(accion=AUDIT_ACTION_ROLE_UNASSIGN) == before + 1
    gr = client.get(f"/api/admin/users/{uid}", headers={"Authorization": f"Bearer {admin_token}"})
    assert gr.status_code == 200
    assert "RolExtraUnassign" in gr.json()["roles"]
