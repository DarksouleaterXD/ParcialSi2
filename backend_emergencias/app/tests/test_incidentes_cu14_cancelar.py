"""CU-14: cancelar solicitud (cliente dueño, estados permitidos)."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_INCIDENTE_CANCELADO_CLIENTE,
    AUDIT_ACTION_INCIDENTE_ELIMINADO_CLIENTE,
    AUDIT_MODULE_SISTEMA,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Rol, Usuario, Vehiculo, usuario_rol


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": f"idem-{uuid.uuid4().hex}"}


def _ensure_vehicle(cliente_id: int, placa: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = db.execute(select(Vehiculo).where(Vehiculo.placa == placa)).scalar_one_or_none()
        if v is not None:
            return v.id
        v = Vehiculo(id_usuario=cliente_id, placa=placa, marca="C", modelo="U14", anio=2021)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _post_incident(client, token: str, vid: int) -> int:
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0, "descripcion_texto": "c14"},
        headers=_hdr(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_cliente_extra(email: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        rol = db.execute(select(Rol).where(Rol.nombre == "Cliente")).scalar_one()
        u = Usuario(
            nombre="Cliente",
            apellido="Extra",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rol.id))
        db.commit()
        return u.id
    finally:
        db.close()


def test_cliente_cancela_pendiente_200_y_bitacora(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14A")
    iid = _post_incident(client, token, vid)
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/cancelar",
        headers=_hdr(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == iid
    assert body["estado"] == "Cancelado"

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = (
            db.execute(
                select(Bitacora).where(
                    Bitacora.id_usuario == 2,
                    Bitacora.modulo == AUDIT_MODULE_SISTEMA,
                    Bitacora.accion == AUDIT_ACTION_INCIDENTE_CANCELADO_CLIENTE,
                ),
            )
            .scalars()
            .first()
        )
        assert row is not None
    finally:
        db.close()

    r2 = client.get(f"/api/incidentes-servicios/incidentes/{iid}", headers=_hdr(token))
    assert r2.json()["estado"] == "Cancelado"


def test_cliente_cancela_en_proceso_409(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14B")
    iid = _post_incident(client, token, vid)
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.execute(update(Incidente).where(Incidente.id == iid).values(estado="En Proceso"))
        db.commit()
    finally:
        db.close()

    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/cancelar",
        headers=_hdr(token),
    )
    assert r.status_code == 409
    assert "curso" in (r.json().get("detail") or "")


def test_otro_cliente_no_cancela_ajeno_403(client):
    _seed_cliente_extra("cliente-otro-cu14@example.com")
    token_dueño = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14C")
    iid = _post_incident(client, token_dueño, vid)
    token_otro = _login(client, "cliente-otro-cu14@example.com")
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/cancelar",
        headers=_hdr(token_otro),
    )
    assert r.status_code == 403


def test_tecnico_no_puede_cancelar_403(client):
    token_t = _login(client, "tecnico-test@example.com")
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14D")
    iid = _post_incident(client, token_c, vid)
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/cancelar",
        headers=_hdr(token_t),
    )
    assert r.status_code == 403


def test_cancelar_inexistente_404(client):
    token = _login(client, "cliente-test@example.com")
    r = client.post(
        "/api/incidentes-servicios/incidentes/99999/cancelar",
        headers=_hdr(token),
    )
    assert r.status_code == 404


def test_ya_cancelado_409(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14E")
    iid = _post_incident(client, token, vid)
    h = _hdr(token)
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/cancelar", headers=h).status_code == 200
    r2 = client.post(f"/api/incidentes-servicios/incidentes/{iid}/cancelar", headers=h)
    assert r2.status_code == 409
    assert "ya fue cancelada" in (r2.json().get("detail") or "")


def test_cliente_cancela_asignado_200(client):
    """Asignado sin avance: cancelable."""
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14F")
    iid = _post_incident(client, token_c, vid)
    token_t = _login(client, "tecnico-test@example.com")
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/aceptar", headers=_hdr(token_t)).status_code == 200
    r = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/cancelar",
        headers=_hdr(token_c),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["estado"] == "Cancelado"
    assert data["tecnico_id"] is not None


def test_cliente_elimina_cancelado_204_y_no_aparece(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14DEL")
    iid = _post_incident(client, token, vid)
    assert client.post(f"/api/incidentes-servicios/incidentes/{iid}/cancelar", headers=_hdr(token)).status_code == 200
    rdel = client.delete(f"/api/incidentes-servicios/incidentes/{iid}", headers=_hdr(token))
    assert rdel.status_code == 204
    rget = client.get(f"/api/incidentes-servicios/incidentes/{iid}", headers=_hdr(token))
    assert rget.status_code == 404
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = (
            db.execute(
                select(Bitacora).where(
                    Bitacora.id_usuario == 2,
                    Bitacora.modulo == AUDIT_MODULE_SISTEMA,
                    Bitacora.accion == AUDIT_ACTION_INCIDENTE_ELIMINADO_CLIENTE,
                ),
            )
            .scalars()
            .first()
        )
        assert row is not None
    finally:
        db.close()


def test_cliente_no_elimina_pendiente_409(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "CU14DEL2")
    iid = _post_incident(client, token, vid)
    rdel = client.delete(f"/api/incidentes-servicios/incidentes/{iid}", headers=_hdr(token))
    assert rdel.status_code == 409
    assert "canceladas o cerradas" in (rdel.json().get("detail") or "").lower()
