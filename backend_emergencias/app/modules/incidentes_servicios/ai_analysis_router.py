"""Rutas HTTP para análisis IA estructurado (Gemini) por incidente."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.incidentes_servicios.ai_analysis_schemas import (
    IncidentAnalysisApiResponse,
    IncidentAnalysisRunRequest,
)
from app.modules.incidentes_servicios.incident_analysis_service import (
    get_latest_incident_structured_ia,
    post_incident_structured_ia_analysis,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import get_current_user

router = APIRouter(prefix="/incidentes-servicios", tags=["incidentes_servicios"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.post(
    "/{incidente_id}/analisis-ia",
    response_model=IncidentAnalysisApiResponse,
    summary="Analizar incidente con IA (Gemini)",
)
def run_structured_incident_analysis(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    body: Annotated[IncidentAnalysisRunRequest | None, Body()] = None,
) -> IncidentAnalysisApiResponse:
    return post_incident_structured_ia_analysis(
        db,
        incidente_id=incidente_id,
        user=user,
        client_ip=_client_ip(request),
        body=body,
    )


@router.get(
    "/{incidente_id}/analisis-ia",
    response_model=IncidentAnalysisApiResponse,
    summary="Obtener último análisis IA del incidente",
)
def get_structured_incident_analysis(
    incidente_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentAnalysisApiResponse:
    return get_latest_incident_structured_ia(db, incidente_id=incidente_id, user=user)
