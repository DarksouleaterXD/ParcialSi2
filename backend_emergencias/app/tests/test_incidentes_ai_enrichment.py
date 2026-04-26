"""Enriquecimiento IA (stub local) tras crear incidente o evidencia (BackgroundTasks)."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_IA_FALLIDA,
    AUDIT_ACTION_IA_PROCESADA,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
)
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str = "cliente-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    h: dict[str, str] = {"Authorization": f"Bearer {token}"}
    h["Idempotency-Key"] = idempotency_key or f"idem-{uuid.uuid4().hex}"
    return h


def _new_vehiculo_cliente() -> int:
    """Un vehículo nuevo por llamada (evita 409 por incidente activo previo)."""
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        placa = ("AI" + uuid.uuid4().hex[:6]).upper()[:20]
        v = Vehiculo(id_usuario=2, placa=placa, marca="Ford", modelo="Ka", anio=2019)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _count_ai_bitacora(accion: str) -> int:
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


def _get_incident(iid: int) -> Incidente | None:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        return db.get(Incidente, iid)
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _uploads_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.services.settings.uploads_dir", str(tmp_path))


def test_create_incident_with_text_classifies_and_prioritizes(client):
    token = _login(client)
    vid = _new_vehiculo_cliente()
    before_ok = _count_ai_bitacora(AUDIT_ACTION_IA_PROCESADA)
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={
            "vehiculo_id": vid,
            "latitud": -34.6,
            "longitud": -58.38,
            "descripcion_texto": "Pinchazo en autopista, ruta 9",
        },
        headers=_hdr(token),
    )
    assert res.status_code == 201
    iid = res.json()["id"]
    assert _count_ai_bitacora(AUDIT_ACTION_IA_PROCESADA) == before_ok + 1
    inc = _get_incident(iid)
    assert inc is not None
    assert inc.categoria_ia == "Neumáticos"
    assert inc.prioridad_ia == "MEDIA"
    assert "Pinchazo" in (inc.resumen_ia or "") or inc.resumen_ia == "Pinchazo reportado."
    assert inc.confianza_ia is not None


def test_create_incident_battery_spanish(client):
    token = _login(client)
    vid = _new_vehiculo_cliente()
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={
            "vehiculo_id": vid,
            "latitud": -34.6,
            "longitud": -58.38,
            "descripcion_texto": "Me quedé sin bateria",
        },
        headers=_hdr(token),
    )
    assert res.status_code == 201
    inc = _get_incident(res.json()["id"])
    assert inc is not None
    assert inc.categoria_ia == "Batería"
    assert inc.prioridad_ia == "ALTA"
    assert "bater" in (inc.resumen_ia or "").lower() or inc.resumen_ia == "Problema de encendido/batería."


def test_add_audio_recomputes_enrichment(client):
    token = _login(client)
    vid = _new_vehiculo_cliente()
    r1 = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0},
        headers=_hdr(token),
    )
    assert r1.status_code == 201
    iid = r1.json()["id"]
    inc0 = _get_incident(iid)
    assert inc0 is not None
    assert inc0.categoria_ia == "Otro"
    fake_mp3 = b"\xff" * 200
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/evidencias",
        data={"tipo": "audio"},
        files={"archivo": ("n.mp3", fake_mp3, "audio/mpeg")},
        headers=_hdr(token),
    )
    assert r2.status_code == 201
    inc = _get_incident(iid)
    assert inc is not None
    assert inc.categoria_ia == "Motor"
    assert inc.prioridad_ia == "MEDIA"


def test_ia_failure_incident_still_created_and_bitacora_failed(monkeypatch: pytest.MonkeyPatch, client):
    def _boom(*args: object, **kwargs: object):
        raise RuntimeError("IA simulada caída")

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_ai_pipeline.analyze_with_google",
        _boom,
    )
    token = _login(client)
    vid = _new_vehiculo_cliente()
    before_fail = _count_ai_bitacora(AUDIT_ACTION_IA_FALLIDA)
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={
            "vehiculo_id": vid,
            "latitud": -35.0,
            "longitud": -59.0,
            "descripcion_texto": "choque leve",
        },
        headers=_hdr(token),
    )
    assert res.status_code == 201
    assert _count_ai_bitacora(AUDIT_ACTION_IA_FALLIDA) == before_fail + 1
    inc = _get_incident(res.json()["id"])
    assert inc is not None
    assert (inc.estado or "").strip().lower() == "revision manual"
    assert (inc.ai_status or "").lower() == "failed"


def test_create_without_description_enriches_with_default_stub(client):
    token = _login(client)
    vid = _new_vehiculo_cliente()
    before_ok = _count_ai_bitacora(AUDIT_ACTION_IA_PROCESADA)
    res = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -30.0, "longitud": -61.0},
        headers=_hdr(token),
    )
    assert res.status_code == 201
    assert _count_ai_bitacora(AUDIT_ACTION_IA_PROCESADA) == before_ok + 1
    inc = _get_incident(res.json()["id"])
    assert inc is not None
    assert inc.categoria_ia == "Otro"
    assert inc.prioridad_ia == "BAJA"
