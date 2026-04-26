"""Progreso de estado del servicio (solo técnico asignado, bitácora)."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_INCIDENTE_EN_CAMINO,
    AUDIT_ACTION_INCIDENTE_EN_PROCESO,
    AUDIT_ACTION_INCIDENTE_FINALIZADO,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": f"idem-{uuid.uuid4().hex}"}


def _user_id_by_email(email: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        u = db.execute(select(Usuario).where(Usuario.email == email)).scalar_one()
        return int(u.id)
    finally:
        db.close()


def _tecnico_b_user_and_token(client):
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        from app.core.security import hash_password
        from app.modules.usuario_autenticacion.models import Rol, usuario_rol

        email = f"tecnico2-svc-{uuid.uuid4().hex[:8]}@example.com"
        u = Usuario(
            nombre="T2",
            apellido="T",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        rt = db.execute(select(Rol).where(Rol.nombre == "Tecnico")).scalar_one()
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rt.id))
        db.commit()
        r = client.post(
            "/api/auth/login",
            json={"email": email, "password": "clave-valida-123"},
        )
        assert r.status_code == 200
        return u.id, r.json()["access_token"]
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
        v = Vehiculo(id_usuario=cliente_id, placa=placa, marca="T", modelo="M1", anio=2021)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _post_and_accept(client, token_c: str, token_t: str, placa: str) -> int:
    vid = _ensure_vehicle(2, placa)
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token_c),
    )
    assert r.status_code == 201, r.text
    iid = r.json()["id"]
    a = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_t),
    )
    assert a.status_code == 200, a.text
    return iid


def _count_bitacora(*, accion: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        from sqlalchemy import func

        return int(
            db.scalar(
                select(func.count())
                .select_from(Bitacora)
                .where(
                    Bitacora.modulo == AUDIT_MODULE_INCIDENTES_SERVICIOS,
                    Bitacora.accion == accion,
                ),
            )
            or 0,
        )
    finally:
        db.close()


def test_progreso_happy_path_en_camino_proceso_final(client):
    token_c = _login(client, "cliente-test@example.com")
    token_t = _login(client, "tecnico-test@example.com")
    n0 = _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_FINALIZADO)
    iid = _post_and_accept(client, token_c, token_t, "P-SVC-OK")

    r1 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-camino",
        headers=_hdr(token_t),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["estado"] == "En Camino"
    n_ec = _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_EN_CAMINO)
    assert n_ec >= 1

    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-proceso",
        headers=_hdr(token_t),
    )
    assert r2.status_code == 200
    assert r2.json()["estado"] == "En Proceso"
    n_ep = _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_EN_PROCESO)
    assert n_ep >= 1

    r3 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/finalizar",
        json={"diagnostico_final": "Batería reemplazada", "precio_base": 15000.5},
        headers=_hdr(token_t),
    )
    assert r3.status_code == 200, r3.text
    b = r3.json()
    assert b["estado"] == "Finalizado"
    assert b["id"] == iid
    n1 = _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_FINALIZADO)
    assert n1 == n0 + 1


def test_tecnico_distinto_403_al_finalizar(client):
    token_c = _login(client, "cliente-test@example.com")
    token_t1 = _login(client, "tecnico-test@example.com")
    iid = _post_and_accept(client, token_c, token_t1, "P-403-OTR")
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        tid1 = _user_id_by_email("tecnico-test@example.com")
        db.execute(
            update(Incidente).where(Incidente.id == iid).values(estado="En Proceso", tecnico_id=tid1),
        )
        db.commit()
    finally:
        db.close()
    _, token_t2 = _tecnico_b_user_and_token(client)
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/finalizar",
        headers=_hdr(token_t2),
    )
    assert r.status_code == 403


def test_no_finalizar_desde_pendiente_o_asignado_solo_en_proceso_409(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "P-SKIP-FIN")
    r0 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token_c),
    )
    iid = r0.json()["id"]
    token_t = _login(client, "tecnico-test@example.com")
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/finalizar",
        headers=_hdr(token_t),
    )
    assert r.status_code == 403
    a = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/aceptar",
        headers=_hdr(token_t),
    )
    assert a.status_code == 200
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/finalizar",
        headers=_hdr(token_t),
    )
    assert r2.status_code == 409
    assert "En Proceso" in (r2.json().get("detail") or "")


def test_marcar_en_proceso_desde_asignado_sin_en_camino_409(client):
    token_c = _login(client, "cliente-test@example.com")
    token_t = _login(client, "tecnico-test@example.com")
    iid = _post_and_accept(client, token_c, token_t, "P-EP-SALT")
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-proceso",
        headers=_hdr(token_t),
    )
    assert r.status_code == 409
    assert "En Camino" in (r.json().get("detail") or "")


def test_administrador_no_puede_marcar_en_camino_sin_ser_tecnico_asignado_403(client):
    token_c = _login(client, "cliente-test@example.com")
    token_t = _login(client, "tecnico-test@example.com")
    token_a = _login(client, "login-test@example.com")
    iid = _post_and_accept(client, token_c, token_t, "ADM-EC-NS")
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-camino",
        headers=_hdr(token_a),
    )
    assert r.status_code == 403


def test_pendiente_admin_no_puede_marcar_en_camino_403(client):
    token_c = _login(client, "cliente-test@example.com")
    token_a = _login(client, "login-test@example.com")
    vid = _ensure_vehicle(2, "P-ADM-PD")
    r0 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token_c),
    )
    iid = r0.json()["id"]
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-camino",
        headers=_hdr(token_a),
    )
    assert r.status_code == 403


def test_cliente_no_puede_marcar_en_camino_403(client):
    token_c = _login(client, "cliente-test@example.com")
    token_t = _login(client, "tecnico-test@example.com")
    iid = _post_and_accept(client, token_c, token_t, "P-CL-BLK")
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/en-camino",
        headers=_hdr(token_c),
    )
    assert r.status_code == 403
