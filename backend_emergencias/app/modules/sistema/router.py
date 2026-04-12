from fastapi import APIRouter

from app.modules.sistema.schemas import ModuloSistemaHealth

router = APIRouter(prefix="/sistema", tags=["sistema"])


@router.get("/health", response_model=ModuloSistemaHealth)
def sistema_health() -> ModuloSistemaHealth:
    return ModuloSistemaHealth(modulo="sistema", status="ok")
