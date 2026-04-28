"""Análisis IA estructurado (Gemini) por incidente: persistencia, bitácora y candidatos a taller."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.incidentes_servicios.ai_analysis_gemini import (
    call_gemini_structured_incident_analysis,
    try_fetch_remote_image,
    try_load_local_image,
)
from app.modules.incidentes_servicios.ai_analysis_schemas import (
    IncidentAnalysisApiResponse,
    IncidentAnalysisRunRequest,
    IncidentStructuredAnalysis,
)
from app.modules.incidentes_servicios.ai_assignment_schemas import AiIncidentResult, CategoriaIncidenteIA
from app.modules.incidentes_servicios.assignment_service import clear_and_persist_candidates, rank_taller_candidates
from app.modules.incidentes_servicios.constants import ESTADO_INICIAL_INCIDENTE, ESTADO_REVISION_MANUAL
from app.modules.incidentes_servicios.models import AnalisisIncidenteIa, Incidente
from app.modules.incidentes_servicios.services import _assert_incident_access, _is_admin, _is_cliente
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_ANALISIS_IA_INCIDENTE,
    AUDIT_ACTION_ASIGNACION_SUGERIDA,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
    registrar_bitacora,
)
from app.modules.usuario_autenticacion.models import Usuario

logger = logging.getLogger(__name__)


def _tipo_display(tipo: str) -> str:
    m = {
        "bateria_descargada": "Batería",
        "pinchazo": "Neumáticos",
        "choque": "Choque / accidente",
        "sobrecalentamiento": "Sobrecalentamiento",
        "falla_motor": "Falla de motor",
        "otro": "Otro",
    }
    return m.get((tipo or "").strip().lower(), "Otro")


def structured_analysis_to_ai_incident_result(s: IncidentStructuredAnalysis) -> AiIncidentResult:
    """Adapta el JSON nuevo al contrato usado por el ranker de talleres existente."""
    tipo = (s.tipo_incidente or "otro").strip().lower()
    cat: CategoriaIncidenteIA
    if tipo == "bateria_descargada":
        cat = "bateria"
    elif tipo == "pinchazo":
        cat = "llanta"
    elif tipo == "choque":
        cat = "choque"
    elif tipo in ("sobrecalentamiento", "falla_motor"):
        cat = "motor"
    else:
        cat = "otro"
    danos = list(s.riesgos_detectados or [])[:30]
    resumen = f"{s.resumen_cliente}\n\n{s.resumen_taller}".strip() or "Sin resumen."
    return AiIncidentResult(
        transcripcion="",
        danos_identificados=danos,
        categoria_incidente=cat,
        resumen_automatico=resumen[:20000],
        confidence=float(s.confianza),
    )


def suggest_workshops_from_structured_analysis(
    db: Session,
    incidente: Incidente,
    analysis: IncidentStructuredAnalysis,
):
    """Calcula ranking y persiste filas en `incidente_taller_candidato`."""
    legacy = structured_analysis_to_ai_incident_result(analysis)
    ar = rank_taller_candidates(db, incidente, legacy)
    clear_and_persist_candidates(db, incidente.id, ar)
    return ar


def build_incident_analysis_context(inc: Incidente, extra_transcription: str | None) -> str:
    lines: list[str] = []
    v = inc.vehiculo
    if v is not None:
        col = (v.color or "").strip() or "n/d"
        lines.append(f"Vehículo: {v.marca} {v.modelo}, año {v.anio}, placa {v.placa}, color {col}")
    lines.append(f"Ubicación reportada: latitud {inc.latitud}, longitud {inc.longitud}")
    lines.append(f"Descripción declarada por el cliente:\n{(inc.descripcion or '').strip() or '(vacía)'}")
    for ev in sorted(inc.evidencias or [], key=lambda x: x.id):
        if (ev.tipo or "").strip().lower() == "texto" and (ev.contenido_texto or "").strip():
            lines.append(f"Nota adicional (evidencia texto):\n{ev.contenido_texto.strip()}")
    if extra_transcription and extra_transcription.strip():
        lines.append(f"Transcripción de audio (proporcionada):\n{extra_transcription.strip()[:50000]}")
    return "\n".join(lines)


def collect_evidence_image_parts(inc: Incidente, uploads_root: Path) -> list[tuple[bytes, str]]:
    out: list[tuple[bytes, str]] = []
    for ev in sorted(inc.evidencias or [], key=lambda x: x.id):
        if (ev.tipo or "").strip().lower() != "foto":
            continue
        rel = (ev.urlarchivo or "").strip()
        if not rel:
            continue
        if rel.startswith(("http://", "https://")):
            got = try_fetch_remote_image(rel)
        else:
            got = try_load_local_image(uploads_root / rel)
        if got:
            out.append(got)
        else:
            logger.info("Sin imagen utilizable para evidencia id=%s path=%s", ev.id, rel[:120])
    return out


def assert_can_post_structured_analysis(user: Usuario, inc: Incidente) -> None:
    if _is_admin(user):
        return
    if not _is_cliente(user) or inc.vehiculo is None or inc.vehiculo.id_usuario != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permiso para ejecutar el análisis IA en este incidente.",
        )


def _persist_failed_analysis_row(db: Session, incidente_id: int, error: str) -> None:
    try:
        row = AnalisisIncidenteIa(
            id_incidente=incidente_id,
            tipo_incidente="otro",
            prioridad="media",
            especialidad_requerida="diagnostico",
            resumen_cliente=None,
            resumen_taller=None,
            recomendaciones_inmediatas=[],
            riesgos_detectados=[],
            confianza=Decimal("0"),
            requiere_grua=False,
            requiere_atencion_inmediata=False,
            modelo_usado=None,
            raw_response=None,
            estado="failed",
            error=(error or "")[:4000],
        )
        db.add(row)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("No se pudo persistir fila de fallo de análisis IA (incidente_id=%s)", incidente_id)


def _row_to_api(incidente_id: int, row: AnalisisIncidenteIa) -> IncidentAnalysisApiResponse:
    rec = row.recomendaciones_inmediatas if isinstance(row.recomendaciones_inmediatas, list) else []
    ries = row.riesgos_detectados if isinstance(row.riesgos_detectados, list) else []
    return IncidentAnalysisApiResponse(
        incidente_id=incidente_id,
        tipo_incidente=row.tipo_incidente,
        prioridad=row.prioridad,
        especialidad_requerida=row.especialidad_requerida,
        resumen_cliente=(row.resumen_cliente or "")[:20000],
        resumen_taller=(row.resumen_taller or "")[:20000],
        recomendaciones_inmediatas=[str(x) for x in rec],
        riesgos_detectados=[str(x) for x in ries],
        confianza=float(row.confianza or 0),
        requiere_grua=bool(row.requiere_grua),
        requiere_atencion_inmediata=bool(row.requiere_atencion_inmediata),
        estado=row.estado,
        modelo_usado=row.modelo_usado,
    )


def post_incident_structured_ia_analysis(
    db: Session,
    *,
    incidente_id: int,
    user: Usuario,
    client_ip: str | None,
    body: IncidentAnalysisRunRequest | None,
) -> IncidentAnalysisApiResponse:
    inc = db.execute(
        select(Incidente)
        .options(selectinload(Incidente.evidencias), selectinload(Incidente.vehiculo))
        .where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    assert_can_post_structured_analysis(user, inc)
    if not (settings.google_ai_api_key or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de IA no está configurado.",
        )

    extra_tx = body.transcripcion_audio if body else None
    ctx = build_incident_analysis_context(inc, extra_tx)
    uploads_root = Path(settings.uploads_dir)
    imgs = collect_evidence_image_parts(inc, uploads_root)

    try:
        analysis, model_used = call_gemini_structured_incident_analysis(context_text=ctx, image_parts=imgs)
    except TimeoutError as exc:
        logger.exception("Timeout Gemini análisis estructurado incidente_id=%s", incidente_id)
        _persist_failed_analysis_row(db, incidente_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El proveedor de IA no respondió correctamente. Intentá más tarde.",
        ) from exc
    except ValueError as exc:
        logger.exception("JSON IA inválido incidente_id=%s", incidente_id)
        _persist_failed_analysis_row(db, incidente_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El proveedor de IA no respondió correctamente. Intentá más tarde.",
        ) from exc
    except RuntimeError as exc:
        logger.exception("Error Gemini análisis estructurado incidente_id=%s", incidente_id)
        _persist_failed_analysis_row(db, incidente_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El proveedor de IA no respondió correctamente. Intentá más tarde.",
        ) from exc

    threshold = float(settings.ai_confidence_threshold or 0.55)
    row_estado = "baja_confianza" if float(analysis.confianza) < threshold else "ok"
    legacy = structured_analysis_to_ai_incident_result(analysis)

    row = AnalisisIncidenteIa(
        id_incidente=incidente_id,
        tipo_incidente=analysis.tipo_incidente,
        prioridad=analysis.prioridad,
        especialidad_requerida=analysis.especialidad_requerida,
        resumen_cliente=analysis.resumen_cliente or None,
        resumen_taller=analysis.resumen_taller or None,
        recomendaciones_inmediatas=list(analysis.recomendaciones_inmediatas or []),
        riesgos_detectados=list(analysis.riesgos_detectados or []),
        confianza=Decimal(str(round(float(analysis.confianza), 4))),
        requiere_grua=bool(analysis.requiere_grua),
        requiere_atencion_inmediata=bool(analysis.requiere_atencion_inmediata),
        modelo_usado=model_used,
        raw_response=json.loads(analysis.model_dump_json()),
        estado=row_estado,
        error=None,
    )

    inc.categoria_ia = _tipo_display(analysis.tipo_incidente)
    inc.prioridad_ia = (analysis.prioridad or "media").capitalize()[:50]
    inc.resumen_ia = f"{analysis.resumen_cliente}\n{analysis.resumen_taller}".strip()[:5000]
    inc.confianza_ia = row.confianza
    inc.ai_confidence = row.confianza
    inc.ai_result_json = legacy.model_dump_json()
    inc.ai_provider = "google_gemini"
    inc.ai_model = model_used
    inc.prompt_version = settings.ai_prompt_version

    if float(analysis.confianza) >= threshold:
        inc.ai_status = "completed"
        inc.estado = ESTADO_INICIAL_INCIDENTE
        ar = suggest_workshops_from_structured_analysis(db, inc, analysis)
        inc.assignment_trace_json = json.dumps({"trace": ar.trace, "weights": ar.weights}, ensure_ascii=False)
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
            accion=AUDIT_ACTION_ASIGNACION_SUGERIDA,
            ip=client_ip,
            resultado=f"OK iid={incidente_id} n={len(ar.candidates)}"[:50],
        )
    else:
        inc.ai_status = "manual_review"
        inc.estado = ESTADO_REVISION_MANUAL

    db.add(row)
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_ANALISIS_IA_INCIDENTE,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} st={row_estado}"[:50],
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error SQL al persistir análisis IA incidente_id=%s", incidente_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el análisis IA.",
        ) from None

    db.refresh(row)
    return _row_to_api(incidente_id, row)


def get_latest_incident_structured_ia(
    db: Session,
    *,
    incidente_id: int,
    user: Usuario,
) -> IncidentAnalysisApiResponse:
    _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    row = db.scalars(
        select(AnalisisIncidenteIa)
        .where(AnalisisIncidenteIa.id_incidente == incidente_id)
        .order_by(AnalisisIncidenteIa.id.desc()),
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay análisis IA guardado para este incidente.",
        )
    return _row_to_api(incidente_id, row)
