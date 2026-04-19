"""Gestión de técnicos por taller (/api/admin/talleres/{id}/technicians)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import app
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_TECHNICIAN_CREATE,
    AUDIT_ACTION_TECHNICIAN_DEACTIVATE,
    AUDIT_ACTION_TECHNICIAN_UPDATE,
    AUDIT_MODULE_TALLER_TECHNICO,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Usuario


def _login(client, email: str = "login-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _taller_body(**kwargs: object) -> dict:
    body: dict = {
        "nombre": "Taller Mec",
        "direccion": "Calle 1",
        "latitud": "-17.78629",
        "longitud": "-63.18117",
        "telefono": "70001234",
        "email": "mec-taller@test.com",
        "capacidad_maxima": 5,
        "horario_atencion": "Lun–Vie",
    }
    body.update(kwargs)
    return body


def _admin_id() -> int:
    engine = app.state.test_engine
    with Session(engine) as db:
        return db.execute(select(Usuario.id).where(Usuario.email == "login-test@example.com")).scalar_one()


def _count_tech_audit(accion: str) -> int:
    engine = app.state.test_engine
    admin_id = _admin_id()
    with Session(engine) as db:
        return int(
            db.execute(
                select(func.count())
                .select_from(Bitacora)
                .where(
                    Bitacora.id_usuario == admin_id,
                    Bitacora.modulo == AUDIT_MODULE_TALLER_TECHNICO,
                    Bitacora.accion == accion,
                ),
            ).scalar_one(),
        )


def test_admin_crea_tecnico(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="T1 Tecnicos"), headers=_hdr(token))
    assert r.status_code == 201
    tid = r.json()["id"]
    before = _count_tech_audit(AUDIT_ACTION_TECHNICIAN_CREATE)
    cr = client.post(
        f"/api/admin/talleres/{tid}/technicians",
        headers=_hdr(token),
        json={
            "nombre": "Juan",
            "apellido": "Mecánico",
            "email": "juan.mec@test.com",
            "telefono": "099111222",
            "especialidad": "battery",
        },
    )
    assert cr.status_code == 201
    body = cr.json()
    assert body["email"] == "juan.mec@test.com"
    assert body["especialidad"] == "battery"
    assert body["taller_id"] == tid
    assert "password_generada" in body and len(body["password_generada"]) > 4
    assert _count_tech_audit(AUDIT_ACTION_TECHNICIAN_CREATE) == before + 1


def test_crear_tecnico_email_duplicado_409(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="T2 Dup"), headers=_hdr(token))
    tid = r.json()["id"]
    payload = {
        "nombre": "A",
        "apellido": "B",
        "email": "dup-mec@test.com",
        "telefono": None,
        "especialidad": "general",
    }
    assert client.post(f"/api/admin/talleres/{tid}/technicians", headers=_hdr(token), json=payload).status_code == 201
    dup = client.post(f"/api/admin/talleres/{tid}/technicians", headers=_hdr(token), json=payload)
    assert dup.status_code == 409


def test_editar_tecnico_y_bitacora(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="T3 Edit"), headers=_hdr(token))
    tid = r.json()["id"]
    cr = client.post(
        f"/api/admin/talleres/{tid}/technicians",
        headers=_hdr(token),
        json={
            "nombre": "Pedro",
            "apellido": "López",
            "email": "pedro.edit@test.com",
            "telefono": None,
            "especialidad": "tires",
        },
    )
    uid = cr.json()["id"]
    before = _count_tech_audit(AUDIT_ACTION_TECHNICIAN_UPDATE)
    up = client.patch(
        f"/api/admin/talleres/{tid}/technicians/{uid}",
        headers=_hdr(token),
        json={"nombre": "Pedro José", "especialidad": "engine"},
    )
    assert up.status_code == 200
    assert up.json()["nombre"] == "Pedro José"
    assert up.json()["especialidad"] == "engine"
    assert _count_tech_audit(AUDIT_ACTION_TECHNICIAN_UPDATE) == before + 1


def test_desactivar_tecnico_soft_delete(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="T4 Baja"), headers=_hdr(token))
    tid = r.json()["id"]
    cr = client.post(
        f"/api/admin/talleres/{tid}/technicians",
        headers=_hdr(token),
        json={
            "nombre": "Ana",
            "apellido": "Rueda",
            "email": "ana.baja@test.com",
            "telefono": None,
            "especialidad": "general",
        },
    )
    uid = cr.json()["id"]
    before = _count_tech_audit(AUDIT_ACTION_TECHNICIAN_DEACTIVATE)
    off = client.post(
        f"/api/admin/talleres/{tid}/technicians/{uid}/desactivar",
        headers=_hdr(token),
    )
    assert off.status_code == 200
    assert off.json()["estado"].lower() == "inactivo"
    assert _count_tech_audit(AUDIT_ACTION_TECHNICIAN_DEACTIVATE) == before + 1


def test_listado_filtra_por_taller(client):
    token = _login(client)
    t1 = client.post("/api/admin/talleres", json=_taller_body(nombre="Tx A"), headers=_hdr(token)).json()["id"]
    t2 = client.post("/api/admin/talleres", json=_taller_body(nombre="Tx B", email="otro@t.com"), headers=_hdr(token)).json()[
        "id"
    ]
    for tid, em in [(t1, "m1@x.com"), (t1, "m2@x.com"), (t2, "m3@x.com")]:
        assert (
            client.post(
                f"/api/admin/talleres/{tid}/technicians",
                headers=_hdr(token),
                json={
                    "nombre": "M",
                    "apellido": "T",
                    "email": em,
                    "telefono": None,
                    "especialidad": "battery",
                },
            ).status_code
            == 201
        )
    lst = client.get(f"/api/admin/talleres/{t1}/technicians?page=1&page_size=50", headers=_hdr(token))
    assert lst.status_code == 200
    assert lst.json()["total"] == 2
    emails = {x["email"] for x in lst.json()["items"]}
    assert emails == {"m1@x.com", "m2@x.com"}


def test_cliente_no_admin_tecnicos_403(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    res = client.get("/api/admin/talleres/1/technicians", headers=_hdr(token))
    assert res.status_code == 403


def test_crear_tecnico_taller_inactivo_409(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="T Inact"), headers=_hdr(token))
    tid = r.json()["id"]
    assert client.post(f"/api/admin/talleres/{tid}/desactivar", headers=_hdr(token)).status_code == 200
    cr = client.post(
        f"/api/admin/talleres/{tid}/technicians",
        headers=_hdr(token),
        json={
            "nombre": "X",
            "apellido": "Y",
            "email": "xy@test.com",
            "telefono": None,
            "especialidad": "general",
        },
    )
    assert cr.status_code == 409
