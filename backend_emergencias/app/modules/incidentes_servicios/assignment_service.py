"""Ranking determinístico de talleres (1.5.5): distancia, especialidad, disponibilidad, ETA."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.incidentes_servicios.ai_assignment_schemas import (
    AiIncidentResult,
    AssignmentCandidate,
    AssignmentResult,
    AssignmentScoreBreakdown,
)
from app.modules.incidentes_servicios.models import Incidente, IncidenteTallerCandidato
from app.modules.taller_tecnico.models import MecanicoTaller, Taller


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _categoria_to_codes(cat: str) -> set[str]:
    k = (cat or "").strip().lower()
    mapping = {
        "bateria": {"battery", "bateria", "electrico"},
        "llanta": {"tires", "llanta", "neumatico", "neumático"},
        "choque": {"body", "chapa", "accident", "collision"},
        "motor": {"engine", "motor", "mecanica"},
        "otro": set(),
    }
    return mapping.get(k, set())


def _priority_component_from_categoria(cat: str) -> float:
    k = (cat or "").strip().lower()
    if k == "choque":
        return 1.0
    if k == "bateria":
        return 0.92
    if k == "motor":
        return 0.78
    if k == "llanta":
        return 0.7
    return 0.45


def _pick_tecnico_for_taller(db: Session, taller_id: int) -> int | None:
    row = db.execute(select(MecanicoTaller).where(MecanicoTaller.id_taller == taller_id).limit(1)).scalar_one_or_none()
    if row is None:
        return None
    return int(row.id_usuario)


def rank_taller_candidates(db: Session, inc: Incidente, ai: AiIncidentResult) -> AssignmentResult:
    lat0 = float(inc.latitud)
    lon0 = float(inc.longitud)
    codes = _categoria_to_codes(ai.categoria_incidente)
    w1 = float(settings.assignment_weight_priority)
    w2 = float(settings.assignment_weight_distance)
    w3 = float(settings.assignment_weight_specialty)
    w4 = float(settings.assignment_weight_availability)
    w5 = float(settings.assignment_weight_eta)
    speed = float(settings.assignment_avg_speed_kmh or 35.0)

    talleres = db.execute(
        select(Taller).where(Taller.disponibilidad.is_(True), Taller.latitud.isnot(None), Taller.longitud.isnot(None)),
    ).scalars().all()

    scored: list[tuple[float, Taller, AssignmentScoreBreakdown, float, float | None]] = []
    for t in talleres:
        lat_t = float(t.latitud)
        lon_t = float(t.longitud)
        dist_km = haversine_km(lat0, lon0, lat_t, lon_t)
        dist_score = max(0.0, 1.0 - min(dist_km, 120.0) / 120.0)
        prio = _priority_component_from_categoria(ai.categoria_incidente)

        esp_rows = db.execute(select(MecanicoTaller).where(MecanicoTaller.id_taller == t.id)).scalars().all()
        esp_vals = {(r.especialidad or "").strip().lower() for r in esp_rows if (r.especialidad or "").strip()}
        if not codes:
            esp_score = 0.55
        else:
            esp_score = 1.0 if esp_vals & codes else 0.35

        disp_score = 1.0 if bool(t.disponibilidad) else 0.0
        eta_h = dist_km / speed if speed > 0 else None
        eta_score = max(0.0, 1.0 - min((eta_h or 0.0), 4.0) / 4.0) if eta_h is not None else 0.5

        breakdown = AssignmentScoreBreakdown(
            prioridad=prio,
            distancia=dist_score,
            especialidad=esp_score,
            disponibilidad=disp_score,
            eta=eta_score,
        )
        total = w1 * prio + w2 * dist_score + w3 * esp_score + w4 * disp_score + w5 * eta_score
        eta_min = (eta_h * 60.0) if eta_h is not None else None
        scored.append((total, t, breakdown, dist_km, eta_min))

    scored.sort(key=lambda x: x[0], reverse=True)
    candidates: list[AssignmentCandidate] = []
    for idx, (total, t, bd, dist_km, eta_min) in enumerate(scored, start=1):
        tid = _pick_tecnico_for_taller(db, int(t.id))
        candidates.append(
            AssignmentCandidate(
                taller_id=int(t.id),
                tecnico_sugerido_id=tid,
                rank=idx,
                score_total=round(float(total), 4),
                breakdown=bd,
                eta_minutos_estimada=float(round(eta_min, 2)) if eta_min is not None else None,
                distancia_km=float(round(dist_km, 3)),
            ),
        )

    trace = {
        "weights": {"prioridad": w1, "distancia": w2, "especialidad": w3, "disponibilidad": w4, "eta": w5},
        "categoria_incidente": ai.categoria_incidente,
        "talleres_evaluados": len(talleres),
    }
    return AssignmentResult(
        incidente_id=int(inc.id),
        candidates=candidates,
        weights={"prioridad": w1, "distancia": w2, "especialidad": w3, "disponibilidad": w4, "eta": w5},
        trace=trace,
    )


def clear_and_persist_candidates(db: Session, incidente_id: int, result: AssignmentResult) -> None:
    db.execute(delete(IncidenteTallerCandidato).where(IncidenteTallerCandidato.id_incidente == incidente_id))
    for c in result.candidates:
        row = IncidenteTallerCandidato(
            id_incidente=incidente_id,
            id_taller=c.taller_id,
            id_tecnico_sugerido=c.tecnico_sugerido_id,
            rank_order=c.rank,
            score_total=Decimal(str(round(c.score_total, 4))),
            score_breakdown_json=json.dumps(c.breakdown.model_dump(), ensure_ascii=False),
            eta_minutos_estimada=Decimal(str(round(c.eta_minutos_estimada, 2))) if c.eta_minutos_estimada is not None else None,
        )
        db.add(row)


def load_incident_for_assignment(db: Session, incidente_id: int) -> Incidente | None:
    return db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()


def assignment_result_from_db(db: Session, incidente_id: int) -> AssignmentResult | None:
    rows = (
        db.execute(
            select(IncidenteTallerCandidato)
            .where(IncidenteTallerCandidato.id_incidente == incidente_id)
            .order_by(IncidenteTallerCandidato.rank_order.asc()),
        )
        .scalars()
        .all()
    )
    if not rows:
        return None
    cands: list[AssignmentCandidate] = []
    for r in rows:
        raw = json.loads(r.score_breakdown_json or "{}")
        bd = AssignmentScoreBreakdown.model_validate(raw)
        cands.append(
            AssignmentCandidate(
                taller_id=int(r.id_taller),
                tecnico_sugerido_id=int(r.id_tecnico_sugerido) if r.id_tecnico_sugerido is not None else None,
                rank=int(r.rank_order),
                score_total=float(r.score_total),
                breakdown=bd,
                eta_minutos_estimada=float(r.eta_minutos_estimada) if r.eta_minutos_estimada is not None else None,
                distancia_km=None,
            ),
        )
    inc = db.get(Incidente, incidente_id)
    trace: dict[str, Any] = {}
    if inc and inc.assignment_trace_json:
        try:
            trace = json.loads(inc.assignment_trace_json)
        except json.JSONDecodeError:
            trace = {}
    return AssignmentResult(incidente_id=incidente_id, candidates=cands, weights=trace.get("weights", {}), trace=trace)
