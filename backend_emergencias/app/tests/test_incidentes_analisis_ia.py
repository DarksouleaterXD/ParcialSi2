"""POST/GET /api/incidentes-servicios/{id}/analisis-ia — análisis estructurado Gemini."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.ai_analysis_schemas import IncidentStructuredAnalysis
from app.modules.incidentes_servicios.models import AnalisisIncidenteIa, Incidente
from app.modules.sistema.bitacora_service import AUDIT_ACTION_ANALISIS_IA_INCIDENTE, AUDIT_MODULE_INCIDENTES_SERVICIOS
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str = "cliente-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _new_vehiculo(id_usuario: int = 2) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        placa = ("IA" + uuid.uuid4().hex[:6]).upper()[:20]
        v = Vehiculo(id_usuario=id_usuario, placa=placa, marca="Ford", modelo="Ka", anio=2019, color="Gris")
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def _create_incidente(vid: int) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc = Incidente(
            id_vehiculo=vid,
            latitud=-34.6,
            longitud=-58.38,
            descripcion="Pinchazo en ruta",
            estado="Pendiente",
            tecnico_id=None,
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        return inc.id
    finally:
        db.close()


def _count_bitacora_analisis() -> int:
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
                    Bitacora.accion == AUDIT_ACTION_ANALISIS_IA_INCIDENTE,
                ),
            )
            or 0,
        )
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _uploads_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.services.settings.uploads_dir", str(tmp_path))
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.uploads_dir", str(tmp_path))


def test_sin_api_key_503(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "")
    iid = _create_incidente(_new_vehiculo())
    token = _login(client)
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 503
    assert r.json().get("detail") == "El servicio de IA no está configurado."


def test_incidente_ajeno_sin_key_sigue_403(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin API key no debe enmascarar 403 por dueño incorrecto."""
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "")
    vid = _new_vehiculo(id_usuario=1)
    iid = _create_incidente(vid)
    token = _login(client, "cliente-test@example.com")
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 403


def test_cliente_no_analiza_incidente_ajeno_403(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    vid = _new_vehiculo(id_usuario=1)
    iid = _create_incidente(vid)
    token = _login(client, "cliente-test@example.com")
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 403


def test_gemini_ok_guarda_analisis_y_bitacora(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    iid = _create_incidente(_new_vehiculo())

    def _fake(*, context_text: str, image_parts: list):
        assert "Pinchazo" in context_text or "ruta" in context_text
        assert image_parts == []
        return (
            IncidentStructuredAnalysis(
                tipo_incidente="pinchazo",
                prioridad="media",
                especialidad_requerida="llantas",
                resumen_cliente="Pinchazo en neumático delantero.",
                resumen_taller="Revisar llanta y válvula.",
                recomendaciones_inmediatas=["Encender balizas"],
                riesgos_detectados=[],
                confianza=0.9,
                requiere_grua=False,
                requiere_atencion_inmediata=False,
            ),
            "gemini-2.0-flash",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_analysis_service.call_gemini_structured_incident_analysis",
        _fake,
    )
    before = _count_bitacora_analisis()
    token = _login(client)
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 200
    data = r.json()
    assert data["incidente_id"] == iid
    assert data["tipo_incidente"] == "pinchazo"
    assert data["confianza"] == 0.9
    assert data["estado"] == "ok"
    assert _count_bitacora_analisis() == before + 1

    Session = sessionmaker(bind=app.state.test_engine)
    db = Session()
    try:
        row = db.scalars(select(AnalisisIncidenteIa).where(AnalisisIncidenteIa.id_incidente == iid)).first()
        assert row is not None
        assert row.id_incidente == iid
        assert row.tipo_incidente == "pinchazo"
    finally:
        db.close()


def test_json_invalido_502(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    iid = _create_incidente(_new_vehiculo())

    def _bad(*, context_text: str, image_parts: list):
        raise ValueError("no json")

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_analysis_service.call_gemini_structured_incident_analysis",
        _bad,
    )
    token = _login(client)
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 502
    Session = sessionmaker(bind=app.state.test_engine)
    db = Session()
    try:
        row = db.scalars(select(AnalisisIncidenteIa).where(AnalisisIncidenteIa.id_incidente == iid)).first()
        assert row is not None and row.estado == "failed"
    finally:
        db.close()


def test_baja_confianza_marca_estado(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.ai_confidence_threshold", 0.55)
    iid = _create_incidente(_new_vehiculo())

    def _low(*, context_text: str, image_parts: list):
        return (
            IncidentStructuredAnalysis(
                tipo_incidente="otro",
                prioridad="baja",
                especialidad_requerida="diagnostico",
                resumen_cliente="Poco claro",
                resumen_taller="Insuficiente",
                recomendaciones_inmediatas=[],
                riesgos_detectados=[],
                confianza=0.2,
                requiere_grua=False,
                requiere_atencion_inmediata=False,
            ),
            "gemini-2.0-flash",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_analysis_service.call_gemini_structured_incident_analysis",
        _low,
    )
    token = _login(client)
    r = client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={})
    assert r.status_code == 200
    assert r.json()["estado"] == "baja_confianza"
    Session = sessionmaker(bind=app.state.test_engine)
    db = Session()
    try:
        inc = db.get(Incidente, iid)
        assert inc is not None
        assert (inc.ai_status or "").lower() == "manual_review"
    finally:
        db.close()


def test_get_ultimo_analisis(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    iid = _create_incidente(_new_vehiculo())

    def _fake(*, context_text: str, image_parts: list):
        return (
            IncidentStructuredAnalysis(
                tipo_incidente="bateria_descargada",
                prioridad="media",
                especialidad_requerida="electricidad",
                resumen_cliente="Batería",
                resumen_taller="Carga o reemplazo",
                recomendaciones_inmediatas=[],
                riesgos_detectados=[],
                confianza=0.88,
                requiere_grua=False,
                requiere_atencion_inmediata=False,
            ),
            "gemini-2.0-flash",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_analysis_service.call_gemini_structured_incident_analysis",
        _fake,
    )
    token = _login(client)
    assert client.post(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token), json={}).status_code == 200
    g = client.get(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token))
    assert g.status_code == 200
    assert g.json()["tipo_incidente"] == "bateria_descargada"


def test_get_sin_analisis_404(client) -> None:
    iid = _create_incidente(_new_vehiculo())
    token = _login(client)
    g = client.get(f"/api/incidentes-servicios/{iid}/analisis-ia", headers=_hdr(token))
    assert g.status_code == 404


def test_transcripcion_opcional_en_contexto(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.incidentes_servicios.incident_analysis_service.settings.google_ai_api_key", "k")
    iid = _create_incidente(_new_vehiculo())
    captured: dict[str, str] = {}

    def _fake(*, context_text: str, image_parts: list):
        captured["ctx"] = context_text
        return (
            IncidentStructuredAnalysis(
                tipo_incidente="otro",
                prioridad="media",
                especialidad_requerida="diagnostico",
                resumen_cliente="x",
                resumen_taller="y",
                recomendaciones_inmediatas=[],
                riesgos_detectados=[],
                confianza=0.9,
                requiere_grua=False,
                requiere_atencion_inmediata=False,
            ),
            "gemini-2.0-flash",
        )

    monkeypatch.setattr(
        "app.modules.incidentes_servicios.incident_analysis_service.call_gemini_structured_incident_analysis",
        _fake,
    )
    token = _login(client)
    r = client.post(
        f"/api/incidentes-servicios/{iid}/analisis-ia",
        headers=_hdr(token),
        json={"transcripcion_audio": "El motor hace ruido raro"},
    )
    assert r.status_code == 200
    assert "Transcripción de audio" in captured["ctx"]
    assert "ruido raro" in captured["ctx"]
