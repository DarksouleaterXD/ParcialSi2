"""Pipeline IA multimodal + transiciones de estado y asignación sugerida (1.5.4 / 1.5.5)."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.incidentes_servicios.ai_assignment_schemas import AiIncidentResult
from app.modules.incidentes_servicios.assignment_service import (
    clear_and_persist_candidates,
    rank_taller_candidates,
)
from app.modules.incidentes_servicios.constants import (
    ESTADO_INICIAL_INCIDENTE,
    ESTADO_REVISION_MANUAL,
)
from app.modules.incidentes_servicios.gemini_incident_ai import analyze_with_google, sanitize_text_for_provider
from app.modules.incidentes_servicios.models import Evidencia, Incidente
from app.modules.sistema.ai_engine import simulate_incident_analysis
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_ASIGNACION_SUGERIDA,
    AUDIT_ACTION_IA_FALLIDA,
    AUDIT_ACTION_IA_PROCESADA,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
    registrar_bitacora,
)

logger = logging.getLogger(__name__)


def _display_categoria(cat: str) -> str:
    m = {
        "bateria": "Batería",
        "llanta": "Neumáticos",
        "choque": "Accidente",
        "motor": "Motor",
        "otro": "Otro",
    }
    return m.get((cat or "").strip().lower(), "Otro")


def _legacy_prioridad(cat: str, ai: AiIncidentResult) -> str:
    k = (cat or "").strip().lower()
    text_hint = {
        "bateria": "bateria",
        "llanta": "pinchazo",
        "choque": "choque",
        "motor": "",
        "otro": "",
    }.get(k, "")
    stub = simulate_incident_analysis(
        text_hint,
        has_audio=bool((ai.transcripcion or "").strip()),
        has_photo=bool(ai.danos_identificados),
    )
    return str(stub.get("prioridad_ia") or "MEDIA")[:50]


def _collect_media_paths(inc: Incidente) -> tuple[list[str], list[str]]:
    audios: list[str] = []
    fotos: list[str] = []
    for ev in sorted(inc.evidencias or [], key=lambda x: x.id):
        tipo = (ev.tipo or "").strip().lower()
        rel = (ev.urlarchivo or "").strip()
        if not rel:
            continue
        if tipo == "audio":
            audios.append(rel)
        elif tipo == "foto":
            fotos.append(rel)
    return audios, fotos


def _combined_description(inc: Incidente) -> str:
    parts: list[str] = []
    if (inc.descripcion or "").strip():
        parts.append(inc.descripcion.strip())
    for ev in sorted(inc.evidencias or [], key=lambda x: x.id):
        if (ev.tipo or "").strip().lower() == "texto" and (ev.contenido_texto or "").strip():
            parts.append(ev.contenido_texto.strip())
    return "\n".join(parts)


def process_incident_ai_pipeline(
    db: Session,
    incidente_id: int,
    *,
    id_usuario_actor: int,
    client_ip: str | None,
    force: bool = False,
) -> tuple[bool, str]:
    """Procesa IA + asignación sugerida. Devuelve (skipped, mensaje_corto)."""
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.evidencias)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None:
        return True, "missing"

    if not force and (inc.ai_status or "").strip().lower() == "completed":
        return True, "already_completed"

    if (inc.ai_status or "").strip().lower() == "processing" and not force:
        return True, "in_progress"

    inc.ai_status = "processing"
    db.commit()

    uploads_root = Path(settings.uploads_dir)

    try:
        combined = _combined_description(inc)
        sanitized = sanitize_text_for_provider(combined)
        audios, fotos = _collect_media_paths(inc)
        result, provider, model_used = analyze_with_google(
            sanitized,
            rutas_audio_relativas=audios,
            rutas_imagen_relativas=fotos,
            uploads_root=uploads_root,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("IA incidente %s falló", incidente_id)
        inc = db.execute(
            select(Incidente).options(selectinload(Incidente.evidencias)).where(Incidente.id == incidente_id),
        ).scalar_one_or_none()
        if inc is None:
            return True, "missing"
        inc.ai_status = "failed"
        inc.ai_provider = "error"
        inc.ai_model = "n/a"
        inc.prompt_version = settings.ai_prompt_version
        inc.estado = ESTADO_REVISION_MANUAL
        inc.ai_result_json = json.dumps({"error": str(exc)[:500]}, ensure_ascii=False)
        registrar_bitacora(
            db,
            id_usuario=id_usuario_actor,
            modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
            accion=AUDIT_ACTION_IA_FALLIDA,
            ip=client_ip,
            resultado=f"ERR iid={incidente_id}"[:50],
        )
        db.commit()
        return False, "failed"

    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.evidencias)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None:
        return True, "missing"

    inc.ai_result_json = result.model_dump_json()
    inc.ai_confidence = Decimal(str(round(float(result.confidence), 4)))
    inc.ai_provider = provider
    inc.ai_model = model_used
    inc.prompt_version = settings.ai_prompt_version
    inc.categoria_ia = _display_categoria(result.categoria_incidente)
    inc.prioridad_ia = _legacy_prioridad(result.categoria_incidente, result)
    inc.resumen_ia = result.resumen_automatico
    inc.confianza_ia = inc.ai_confidence

    threshold = float(settings.ai_confidence_threshold or 0.55)
    if float(result.confidence) < threshold:
        inc.ai_status = "manual_review"
        inc.estado = ESTADO_REVISION_MANUAL
        registrar_bitacora(
            db,
            id_usuario=id_usuario_actor,
            modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
            accion=AUDIT_ACTION_IA_PROCESADA,
            ip=client_ip,
            resultado=f"LOW iid={incidente_id} c={result.confidence:.2f}"[:50],
        )
        db.commit()
        return False, "manual_review"

    inc.ai_status = "completed"
    inc.estado = ESTADO_INICIAL_INCIDENTE
    ar = rank_taller_candidates(db, inc, result)
    inc.assignment_trace_json = json.dumps({"trace": ar.trace, "weights": ar.weights}, ensure_ascii=False)
    clear_and_persist_candidates(db, incidente_id, ar)
    registrar_bitacora(
        db,
        id_usuario=id_usuario_actor,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_IA_PROCESADA,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} p={provider}"[:50],
    )
    registrar_bitacora(
        db,
        id_usuario=id_usuario_actor,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_ASIGNACION_SUGERIDA,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} n={len(ar.candidates)}"[:50],
    )
    db.commit()
    return False, "completed"


def reload_incident(db: Session, incidente_id: int) -> Incidente | None:
    return db.execute(
        select(Incidente).options(selectinload(Incidente.evidencias)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
