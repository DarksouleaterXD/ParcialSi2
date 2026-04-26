"""CU10: listado técnico, aceptar y rechazar incidentes."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_INCIDENTE_ACEPTADO,
    AUDIT_ACTION_INCIDENTE_RECHAZADO,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
)
from app.modules.sistema.models import Bitacora
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Rol, Usuario, Vehiculo, usuario_rol


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": f"idem-{uuid.uuid4().hex}"}


def _tecnico_user_id() -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        u = db.execute(select(Usuario).where(Usuario.email == "tecnico-test@example.com")).scalar_one()
        return int(u.id)
    finally:
        db.close()


def _ensure_vehicle(cliente_id: int, placa: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = db.execute(select(Vehiculo).where(Vehiculo.placa == placa)).scalar_one_or_none()
        if v is not None:
            return v.id
        v = Vehiculo(id_usuario=cliente_id, placa=placa, marca="T", modelo="X", anio=2020)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _seed_tecnico_without_taller(email: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        rt = db.execute(select(Rol).where(Rol.nombre == "Tecnico")).scalar_one()
        u = Usuario(
            nombre="Tec",
            apellido="SinTaller",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rt.id))
        db.commit()
        return int(u.id)
    finally:
        db.close()


def _seed_tecnico_with_taller(email: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        rt = db.execute(select(Rol).where(Rol.nombre == "Tecnico")).scalar_one()
        u = Usuario(
            nombre="Tec",
            apellido="ConTaller",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rt.id))
        t = Taller(
            id_admin=1,
            nombre=f"Taller-{u.id}",
            direccion="Dir",
            latitud=-34.61,
            longitud=-58.39,
            disponibilidad=True,
            capacidad_max=5,
            calificacion=0,
        )
        db.add(t)
        db.flush()
        db.add(MecanicoTaller(id_usuario=u.id, id_taller=t.id, especialidad="motor"))
        db.commit()
        return int(u.id)
    finally:
        db.close()


def _post_incident(client, token: str, vid: int) -> int:
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token),
    )
    assert r.status_code == 201
    return r.json()["id"]


def _count_bitacora(accion: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        return int(
            db.scalar(
                select(func.count())
                .select_from(Bitacora)
                .where(Bitacora.modulo == AUDIT_MODULE_INCIDENTES_SERVICIOS, Bitacora.accion == accion),
            )
            or 0,
        )
    finally:
        db.close()


def test_tecnico_list_forbidden_cliente_filters(client):
    token_t = _login(client, "tecnico-test@example.com")
    r = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"cliente_busqueda": "x"},
        headers=_hdr(token_t),
    )
    assert r.status_code == 403


def test_cliente_cannot_accept_or_reject(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10C")
    iid = _post_incident(client, token_c, vid)
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_c)).status_code == 403
    assert (
        client.post(f"/api/incidentes-servicios/incidentes/{iid}/rechazar", headers=_hdr(token_c)).status_code == 403
    )


def test_tecnico_accept_assigns_and_bitacora(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10A")
    iid = _post_incident(client, token_c, vid)
    tid = _tecnico_user_id()
    before = _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO)
    token_t = _login(client, "tecnico-test@example.com")
    r = client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_t))
    assert r.status_code == 200
    j = r.json()
    assert j["estado"] == "Asignado"
    assert j["tecnico_id"] == tid
    assert _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO) == before + 1


def test_tecnico_without_taller_cannot_accept(client):
    _seed_tecnico_without_taller("tecnico-sin-taller-cu10@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10NT")
    iid = _post_incident(client, token_c, vid)
    before = _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO)
    token_t = _login(client, "tecnico-sin-taller-cu10@example.com")
    r = client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_t))
    assert r.status_code == 403
    assert "asignado a un taller" in (r.json().get("detail") or "").lower()
    assert _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO) == before


def test_double_accept_second_409(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10D")
    iid = _post_incident(client, token_c, vid)
    token_t1 = _login(client, "tecnico-test@example.com")
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_t1)).status_code == 200
    token_a = _login(client, "login-test@example.com")
    tid = _tecnico_user_id()
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_a),
        json={"tecnico_id": tid},
    )
    assert r2.status_code == 409


def test_tecnico_reject_ok_and_bitacora(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10R")
    iid = _post_incident(client, token_c, vid)
    before = _count_bitacora(AUDIT_ACTION_INCIDENTE_RECHAZADO)
    token_t = _login(client, "tecnico-test@example.com")
    r = client.post(f"/api/incidentes-servicios/incidentes/{iid}/rechazar", headers=_hdr(token_t))
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert _count_bitacora(AUDIT_ACTION_INCIDENTE_RECHAZADO) == before + 1
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc = db.get(Incidente, iid)
        assert inc is not None
        assert (inc.estado or "").strip() == "Pendiente"
        assert inc.tecnico_id is None
    finally:
        db.close()


def test_admin_reject_forbidden(client):
    token_a = _login(client, "login-test@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10AR")
    iid = _post_incident(client, token_c, vid)
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/rechazar", headers=_hdr(token_a)).status_code == 403


def test_admin_accept_requires_tecnico_id(client):
    token_a = _login(client, "login-test@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10ADM")
    iid = _post_incident(client, token_c, vid)
    r = client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_a), json={})
    assert r.status_code == 422
    tid = _tecnico_user_id()
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_a),
        json={"tecnico_id": tid},
    )
    assert r2.status_code == 200
    assert r2.json()["tecnico_id"] == tid


def test_admin_accept_rejects_tecnico_without_taller(client):
    tid = _seed_tecnico_without_taller("tecnico-admin-sin-taller-cu10@example.com")
    token_a = _login(client, "login-test@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10ASN")
    iid = _post_incident(client, token_c, vid)
    before = _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO)
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_a),
        json={"tecnico_id": tid},
    )
    assert r.status_code == 403
    assert "asignado a un taller" in (r.json().get("detail") or "").lower()
    assert _count_bitacora(AUDIT_ACTION_INCIDENTE_ACEPTADO) == before


def test_admin_accept_with_tecnico_linked_success(client):
    tid = _seed_tecnico_with_taller("tecnico-admin-con-taller-cu10@example.com")
    token_a = _login(client, "login-test@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU10ACT")
    iid = _post_incident(client, token_c, vid)
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_a),
        json={"tecnico_id": tid},
    )
    assert r.status_code == 200
    assert r.json()["tecnico_id"] == tid
