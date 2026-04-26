"""Asignación determinística, confirmación, override e idempotencia del pipeline IA (1.5.4 / 1.5.5)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.ai_assignment_schemas import AiIncidentResult
from app.modules.incidentes_servicios.assignment_service import rank_taller_candidates
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.bitacora_service import AUDIT_ACTION_ASIGNACION_SUGERIDA
from app.modules.sistema.models import Bitacora
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": f"idem-{uuid.uuid4().hex}"}


def _new_vehiculo_cliente() -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        placa = ("AS" + uuid.uuid4().hex[:6]).upper()[:20]
        v = Vehiculo(id_usuario=2, placa=placa, marca="Ford", modelo="Ka", anio=2019)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _seed_two_talleres_with_mecanicos() -> tuple[int, int]:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        t_near = Taller(
            id_admin=1,
            nombre=f"Near{uuid.uuid4().hex[:4]}",
            direccion="d1",
            latitud=Decimal("-34.600000"),
            longitud=Decimal("-58.380000"),
            disponibilidad=True,
            capacidad_max=5,
        )
        t_far = Taller(
            id_admin=1,
            nombre=f"Far{uuid.uuid4().hex[:4]}",
            direccion="d2",
            latitud=Decimal("-36.000000"),
            longitud=Decimal("-58.380000"),
            disponibilidad=True,
            capacidad_max=5,
        )
        db.add(t_near)
        db.add(t_far)
        db.commit()
        db.refresh(t_near)
        db.refresh(t_far)
        db.add(MecanicoTaller(id_usuario=3, id_taller=t_near.id, especialidad="tires"))
        db.add(MecanicoTaller(id_usuario=3, id_taller=t_far.id, especialidad="tires"))
        db.commit()
        return int(t_near.id), int(t_far.id)
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _uploads_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr("app.modules.incidentes_servicios.services.settings.uploads_dir", str(tmp_path))


def test_ranking_prefers_closer_taller(client):
    _seed_two_talleres_with_mecanicos()
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        vid = _new_vehiculo_cliente()
        inc = Incidente(
            id_vehiculo=vid,
            latitud=Decimal("-34.600000"),
            longitud=Decimal("-58.380000"),
            descripcion="pinchazo",
            estado="Pendiente",
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        ai = AiIncidentResult(
            transcripcion="",
            danos_identificados=[],
            categoria_incidente="llanta",
            resumen_automatico="test",
            confidence=0.9,
        )
        ar = rank_taller_candidates(db, inc, ai)
        assert len(ar.candidates) >= 2
        assert ar.candidates[0].distancia_km is not None
        assert ar.candidates[1].distancia_km is not None
        assert ar.candidates[0].distancia_km <= ar.candidates[1].distancia_km
    finally:
        db.close()


def test_low_confidence_sets_manual_review(client, monkeypatch):
    def _low(*args: object, **kwargs: object):
        return (
            AiIncidentResult(
                transcripcion="",
                danos_identificados=[],
                categoria_incidente="otro",
                resumen_automatico="x",
                confidence=0.1,
            ),
            "test_provider",
            "test_model",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_ai_pipeline.analyze_with_google",
        _low,
    )
    token = _login(client, "cliente-test@example.com")
    vid = _new_vehiculo_cliente()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.0, "longitud": -58.0, "descripcion_texto": "x"},
        headers=_hdr(token),
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc = db.get(Incidente, iid)
        assert inc is not None
        assert (inc.ai_status or "").lower() == "manual_review"
        assert (inc.estado or "").strip().lower() == "revision manual"
    finally:
        db.close()


def test_confirm_assignment_admin(client):
    _seed_two_talleres_with_mecanicos()
    token_c = _login(client, "cliente-test@example.com")
    vid = _new_vehiculo_cliente()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={
            "vehiculo_id": vid,
            "latitud": -34.6,
            "longitud": -58.38,
            "descripcion_texto": "Pinchazo en ruta 9",
        },
        headers=_hdr(token_c),
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc_row = db.get(Incidente, iid)
        assert inc_row is not None
        assert (inc_row.ai_status or "").lower() == "completed"
    finally:
        db.close()

    token_a = _login(client, "login-test@example.com")
    cand = client.get(f"/api/incidentes-servicios/incidentes/{iid}/asignacion/candidatos", headers=_hdr(token_a))
    assert cand.status_code == 200
    items = cand.json()["candidates"]
    assert len(items) >= 1
    top_taller = items[0]["taller_id"]
    conf = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/asignacion/confirmar",
        json={"taller_id": top_taller},
        headers=_hdr(token_a),
    )
    assert conf.status_code == 200
    assert conf.json()["estado"] == "Asignado"
    assert conf.json()["tecnico_id"] == 3


def test_override_forbidden_for_cliente(client):
    tid_near, _ = _seed_two_talleres_with_mecanicos()
    token_c = _login(client, "cliente-test@example.com")
    vid = _new_vehiculo_cliente()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.6, "longitud": -58.38, "descripcion_texto": "choque leve"},
        headers=_hdr(token_c),
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    ov = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/asignacion/override",
        json={"taller_id": tid_near, "tecnico_id": 3},
        headers=_hdr(token_c),
    )
    assert ov.status_code == 403


def test_override_admin_after_manual_review(client, monkeypatch):
    def _low(*args: object, **kwargs: object):
        return (
            AiIncidentResult(
                transcripcion="",
                danos_identificados=[],
                categoria_incidente="otro",
                resumen_automatico="dudoso",
                confidence=0.2,
            ),
            "t",
            "m",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.gemini_incident_ai.analyze_with_google",
        _low,
    )
    tid_near, _ = _seed_two_talleres_with_mecanicos()
    token_c = _login(client, "cliente-test@example.com")
    vid = _new_vehiculo_cliente()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.6, "longitud": -58.38, "descripcion_texto": "x"},
        headers=_hdr(token_c),
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    token_a = _login(client, "login-test@example.com")
    ov = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/asignacion/override",
        json={"taller_id": tid_near, "tecnico_id": 3},
        headers=_hdr(token_a),
    )
    assert ov.status_code == 200
    assert ov.json()["estado"] == "Asignado"
    assert ov.json()["tecnico_id"] == 3


def test_ia_reprocess_idempotent_no_duplicate_sugerida(client):
    _seed_two_talleres_with_mecanicos()
    token_c = _login(client, "cliente-test@example.com")
    vid = _new_vehiculo_cliente()
    r = client.post(
        "/api/incidentes-servicios/incidentes",
        json={"vehiculo_id": vid, "latitud": -34.6, "longitud": -58.38, "descripcion_texto": "batería muerta"},
        headers=_hdr(token_c),
    )
    assert r.status_code == 201
    iid = r.json()["id"]

    def count_asign_sugerida() -> int:
        engine = app.state.test_engine
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            return int(
                db.scalar(
                    select(func.count()).select_from(Bitacora).where(Bitacora.accion == AUDIT_ACTION_ASIGNACION_SUGERIDA),
                )
                or 0,
            )
        finally:
            db.close()

    n0 = count_asign_sugerida()
    token_a = _login(client, "login-test@example.com")
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/ia/process",
        headers=_hdr(token_a),
    )
    assert r2.status_code == 200
    assert r2.json().get("skipped") is True
    assert count_asign_sugerida() == n0
