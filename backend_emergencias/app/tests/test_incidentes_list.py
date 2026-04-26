"""GET /api/incidentes-servicios/incidentes — listado, filtros, paginación y permisos."""

import uuid
from datetime import date, datetime, time

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    h: dict[str, str] = {"Authorization": f"Bearer {token}"}
    h["Idempotency-Key"] = idempotency_key or f"idem-{uuid.uuid4().hex}"
    return h


def _ensure_vehicle(cliente_id: int, placa: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = db.execute(select(Vehiculo).where(Vehiculo.placa == placa)).scalar_one_or_none()
        if v is not None:
            return v.id
        v = Vehiculo(
            id_usuario=cliente_id,
            placa=placa,
            marca="Test",
            modelo="X",
            anio=2020,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
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


def test_list_pagination(client):
    token = _login(client, "cliente-test@example.com")
    v1 = _ensure_vehicle(2, "LST01")
    v2 = _ensure_vehicle(2, "LST02")
    v3 = _ensure_vehicle(2, "LST03")
    _post_incident(client, token, v1)
    _post_incident(client, token, v2)
    _post_incident(client, token, v3)
    r = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"page": 1, "page_size": 2},
        headers=_hdr(token),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["page"] == 1
    assert j["page_size"] == 2
    assert j["total"] >= 3
    assert len(j["items"]) == 2
    r2 = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"page": 2, "page_size": 2},
        headers=_hdr(token),
    )
    assert r2.status_code == 200
    assert len(r2.json()["items"]) >= 1


def test_list_filter_estado(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "LST04")
    iid = _post_incident(client, token, vid)
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.execute(update(Incidente).where(Incidente.id == iid).values(estado="Cerrado"))
        db.commit()
    finally:
        db.close()
    r_all = client.get("/api/incidentes-servicios/incidentes", headers=_hdr(token))
    assert r_all.status_code == 200
    r_f = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"estado": "Cerrado"},
        headers=_hdr(token),
    )
    assert r_f.status_code == 200
    ids = {x["id"] for x in r_f.json()["items"]}
    assert iid in ids
    for row in r_f.json()["items"]:
        if row["id"] == iid:
            assert row["estado"] == "Cerrado"


def test_list_filter_fechas(client):
    token = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "LST05")
    iid = _post_incident(client, token, vid)
    d = date(2024, 6, 15)
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.execute(update(Incidente).where(Incidente.id == iid).values(fechacreacion=datetime.combine(d, time(12, 0, 0))))
        db.commit()
    finally:
        db.close()
    r_out = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"fecha_desde": "2024-06-20", "fecha_hasta": "2024-06-30"},
        headers=_hdr(token),
    )
    assert r_out.status_code == 200
    assert iid not in {x["id"] for x in r_out.json()["items"]}
    r_in = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"fecha_desde": "2024-06-01", "fecha_hasta": "2024-06-20"},
        headers=_hdr(token),
    )
    assert r_in.status_code == 200
    assert iid in {x["id"] for x in r_in.json()["items"]}


def test_list_filter_cliente_admin(client):
    token_c = _login(client, "cliente-test@example.com")
    token_a = _login(client, "login-test@example.com")
    vid = _ensure_vehicle(2, "LST06")
    iid = _post_incident(client, token_c, vid)
    r = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"cliente": 2},
        headers=_hdr(token_a),
    )
    assert r.status_code == 200
    assert iid in {x["id"] for x in r.json()["items"]}
    r_empty = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"cliente": 99999},
        headers=_hdr(token_a),
    )
    assert r_empty.status_code == 200
    assert r_empty.json()["total"] == 0


def test_list_filter_cliente_busqueda_admin(client):
    token_c = _login(client, "cliente-test@example.com")
    token_a = _login(client, "login-test@example.com")
    placa = "LSTCB" + uuid.uuid4().hex[:6].upper()
    vid = _ensure_vehicle(2, placa)
    iid = _post_incident(client, token_c, vid)
    r_mail = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"cliente_busqueda": "cliente-test"},
        headers=_hdr(token_a),
    )
    assert r_mail.status_code == 200
    assert iid in {x["id"] for x in r_mail.json()["items"]}
    r_nombre = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"cliente_busqueda": "Cliente"},
        headers=_hdr(token_a),
    )
    assert r_nombre.status_code == 200
    assert iid in {x["id"] for x in r_nombre.json()["items"]}


def test_list_filter_vehiculo_placa(client):
    token = _login(client, "cliente-test@example.com")
    placa = "LSTPL" + uuid.uuid4().hex[:6].upper()
    vid = _ensure_vehicle(2, placa)
    iid = _post_incident(client, token, vid)
    r = client.get(
        "/api/incidentes-servicios/incidentes",
        params={"vehiculo_placa": placa[3:8]},
        headers=_hdr(token),
    )
    assert r.status_code == 200
    assert iid in {x["id"] for x in r.json()["items"]}


def test_list_cliente_only_own(client):
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = Vehiculo(id_usuario=1, placa="LSTADM", marca="X", modelo="Y", anio=2020)
        db.add(v)
        db.flush()
        inc = Incidente(
            id_vehiculo=v.id,
            latitud=Decimal("-34.0"),
            longitud=Decimal("-58.0"),
            descripcion="otro",
            estado="Finalizado",
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        iid_other = inc.id
    finally:
        db.close()
    token_c = _login(client, "cliente-test@example.com")
    r = client.get("/api/incidentes-servicios/incidentes", headers=_hdr(token_c))
    assert r.status_code == 200
    assert iid_other not in {x["id"] for x in r.json()["items"]}


def test_list_tecnico_sees_pool_and_assigned(client):
    token_c = _login(client, "cliente-test@example.com")
    vid = _ensure_vehicle(2, "TECPOOL")
    iid = _post_incident(client, token_c, vid)
    token_t = _login(client, "tecnico-test@example.com")
    r = client.get("/api/incidentes-servicios/incidentes", headers=_hdr(token_t))
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()["items"]}
    assert iid in ids


def test_list_query_invalid_422(client):
    token = _login(client, "cliente-test@example.com")
    assert (
        client.get(
            "/api/incidentes-servicios/incidentes",
            params={"page": 0},
            headers=_hdr(token),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/incidentes-servicios/incidentes",
            params={"page_size": 101},
            headers=_hdr(token),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/incidentes-servicios/incidentes",
            params={"fecha_desde": "not-a-date"},
            headers=_hdr(token),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/incidentes-servicios/incidentes",
            params={"cliente_busqueda": "x" * 101},
            headers=_hdr(token),
        ).status_code
        == 422
    )


def test_list_requires_auth(client):
    assert client.get("/api/incidentes-servicios/incidentes").status_code == 401
