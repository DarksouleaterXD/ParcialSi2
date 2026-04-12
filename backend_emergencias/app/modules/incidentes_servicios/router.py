from fastapi import APIRouter

from app.modules.incidentes_servicios.schemas import IncidentesHealth

router = APIRouter(prefix="/incidentes-servicios", tags=["incidentes_servicios"])


@router.get("/health", response_model=IncidentesHealth)
def incidentes_health() -> IncidentesHealth:
    return IncidentesHealth(modulo="incidentes_servicios", status="stub")
