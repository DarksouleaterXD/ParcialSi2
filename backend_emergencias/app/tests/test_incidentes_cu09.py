"""CU-09: crear incidente, evidencias y bitácora."""

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_EVIDENCIA_ADD,
    AUDIT_ACTION_INCIDENTE_CREATE,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str = "cliente-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _vehiculo_id_for_cliente() -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        u = db.execute(select(Vehiculo).where(Vehiculo.id_usuario == 2)).scalar_one_or_none()
        if u is not None:
            return u.id
        v = Vehiculo(
            id_usuario=2,
            placa="CU09XY",
            marca="Ford",
            modelo="Ka",
            anio=2019,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _count_bitacora(*, accion: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
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


@pytest.fixture(autouse=True)
def _uploads_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.services.settings.uploads_dir", str(tmp_path))


def test_create_incident_happy_201(client):
    token = _login(client)
    vid = _vehiculo_id_for_cliente()
    before = _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_CREATE)
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={
            "vehiculo_id": vid,
            "latitud": -34.6037,
            "longitud": -58.3816,
            "descripcion_texto": "Pinchazo en autopista",
        },
        headers=_hdr(token),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["vehiculo_id"] == vid
    assert body["cliente_id"] == 2
    assert body["estado"] == "Pendiente"
    assert body["evidencias_count"] == 0
    assert body["descripcion_texto"] == "Pinchazo en autopista"
    assert _count_bitacora(accion=AUDIT_ACTION_INCIDENTE_CREATE) == before + 1


def test_create_incident_foreign_vehicle_403(client):
    token_admin = _login(client, "login-test@example.com", "clave-valida-123")
    vid = _vehiculo_id_for_cliente()
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token_admin),
    )
    assert res.status_code == 403


def test_create_incident_invalid_coords_422(client):
    token = _login(client)
    vid = _vehiculo_id_for_cliente()
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": 91.0, "longitud": -58.0},
        headers=_hdr(token),
    )
    assert res.status_code == 422


def test_add_evidence_text_201_and_bitacora(client):
    token = _login(client)
    vid = _vehiculo_id_for_cliente()
    r1 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.1, "longitud": -58.1, "descripcion_texto": None},
        headers=_hdr(token),
    )
    assert r1.status_code == 201
    iid = r1.json()["id"]
    before_ev = _count_bitacora(accion=AUDIT_ACTION_EVIDENCIA_ADD)
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "texto", "contenido_texto": "  Nota del conductor  "},
        headers=_hdr(token),
    )
    assert res.status_code == 201
    j = res.json()
    assert j["incidente_id"] == iid
    assert j["tipo"] == "texto"
    assert j["url_or_path"] == ""
    assert _count_bitacora(accion=AUDIT_ACTION_EVIDENCIA_ADD) == before_ev + 1


def test_add_evidence_file_201(client):
    token = _login(client)
    vid = _vehiculo_id_for_cliente()
    r1 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.2, "longitud": -58.2},
        headers=_hdr(token),
    )
    iid = r1.json()["id"]
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 120 + b"\xff\xd9"
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "foto"},
        files={"archivo": ("x.jpg", fake_jpeg, "image/jpeg")},
        headers=_hdr(token),
    )
    assert res.status_code == 201
    assert res.json()["tipo"] == "foto"
    assert res.json()["url_or_path"].startswith(f"incidentes/{iid}/")


def test_add_evidence_incident_not_found_404(client):
    token = _login(client)
    res = client.post(
        "/api/incidentes-servicios/incidentes/99999/evidencias",
        data={"tipo": "texto", "contenido_texto": "x"},
        headers=_hdr(token),
    )
    assert res.status_code == 404


def test_create_incident_409_when_vehicle_has_active(client):
    token = _login(client)
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = Vehiculo(
            id_usuario=2,
            placa="CU09ZZ",
            marca="VW",
            modelo="Gol",
            anio=2018,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        vid = v.id
    finally:
        db.close()
    assert (
        client.post(
            "/api/incidentes-servicios/incidentes",
            json={"vehiculo_id": vid, "latitud": -31.0, "longitud": -60.0},
            headers=_hdr(token),
        ).status_code
        == 201
    )
    res2 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -31.1, "longitud": -60.1},
        headers=_hdr(token),
    )
    assert res2.status_code == 409
    assert "activo" in res2.json()["detail"].lower()


def test_get_incident_detail_includes_evidencias(client):
    token = _login(client)
    vid = _vehiculo_id_for_cliente()
    r1 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -33.0, "longitud": -59.0},
        headers=_hdr(token),
    )
    iid = r1.json()["id"]
    client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "texto", "contenido_texto": "ev1"},
        headers=_hdr(token),
    )
    r2 = client.get(f"/api/incidentes-servicios/incidentes/{iid}", headers=_hdr(token))
    assert r2.status_code == 200
    d = r2.json()
    assert d["id"] == iid
    assert d["evidencias_count"] == 1
    assert len(d["evidencias"]) == 1
    assert d["evidencias"][0]["tipo"] == "texto"
