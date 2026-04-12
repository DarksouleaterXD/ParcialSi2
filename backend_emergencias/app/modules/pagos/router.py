from fastapi import APIRouter

from app.modules.pagos.schemas import PagosHealth

router = APIRouter(prefix="/pagos", tags=["pagos"])


@router.get("/health", response_model=PagosHealth)
def pagos_health() -> PagosHealth:
    return PagosHealth(modulo="pagos", status="stub")
