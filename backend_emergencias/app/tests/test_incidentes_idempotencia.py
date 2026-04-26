"""Idempotencia POST incidentes y evidencias (P2)."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Evidencia
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str = "cliente-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    h: dict[str, str] = {"Authorization": f"Bearer {token}"}
    h["Idempotency-Key"] = idempotency_key or f"idem-{uuid.uuid4().hex}"
    return h


def _new_vehicle(cliente_id: int = 2) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        placa = ("ID" + uuid.uuid4().hex[:6]).upper()[:20]
        v = Vehiculo(id_usuario=cliente_id, placa=placa, marca="VW", modelo="Gol", anio=2020)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _count_evidencias_incidente(incidente_id: int) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        return int(
            db.scalar(select(func.count()).select_from(Evidencia).where(Evidencia.id_incidente == incidente_id)) or 0,
        )
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _uploads_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.services.settings.uploads_dir", str(tmp_path))


def test_double_submit_incident_same_key_no_duplicate(client):
    token = _login(client)
    vid = _new_vehicle()
    key = f"idem-mobile-{uuid.uuid4().hex}"
    body = {"vehiculo_id": vid, "latitud": -32.0, "longitud": -60.0, "descripcion_texto": "dup test"}
    r1 = client.post("/api/incidentes-servicios/incidentes", json=body, headers=_hdr(token, idempotency_key=key))
    assert r1.status_code == 201
    iid = r1.json()["id"]
    r2 = client.post("/api/incidentes-servicios/incidentes", json=body, headers=_hdr(token, idempotency_key=key))
    assert r2.status_code == 200
    assert r2.json()["id"] == iid


def test_same_idempotency_key_different_body_409(client):
    token = _login(client)
    v1 = _new_vehicle()
    v2 = _new_vehicle()
    key = f"idem-conflict-{uuid.uuid4().hex}"
    r1 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": v1, "latitud": -31.0, "longitud": -61.0},
        headers=_hdr(token, idempotency_key=key),
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": v2, "latitud": -31.0, "longitud": -61.0},
        headers=_hdr(token, idempotency_key=key),
    )
    assert r2.status_code == 409


def test_double_upload_evidence_same_content_no_duplicate(client):
    token = _login(client)
    vid = _new_vehicle()
    r0 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -30.0, "longitud": -62.0},
        headers=_hdr(token),
    )
    assert r0.status_code == 201
    iid = r0.json()["id"]
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 120 + b"\xff\xd9"
    before = _count_evidencias_incidente(iid)
    r1 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "foto"},
        files={"archivo": ("x.jpg", fake_jpeg, "image/jpeg")},
        headers=_hdr(token),
    )
    assert r1.status_code == 201
    eid = r1.json()["id"]
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "foto"},
        files={"archivo": ("y.jpg", fake_jpeg, "image/jpeg")},
        headers=_hdr(token),
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == eid
    assert _count_evidencias_incidente(iid) == before + 1


def test_invalid_idempotency_key_422(client):
    token = _login(client)
    vid = _new_vehicle()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -29.0, "longitud": -63.0},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "short"},
    )
    assert r.status_code == 422
