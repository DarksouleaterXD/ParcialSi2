from fastapi import APIRouter

from app.modules.taller_tecnico.schemas import TallerTecnicoHealth

router = APIRouter(prefix="/taller-tecnico", tags=["taller_tecnico"])


@router.get("/health", response_model=TallerTecnicoHealth)
def taller_tecnico_health() -> TallerTecnicoHealth:
    return TallerTecnicoHealth(modulo="taller_tecnico", status="stub")
