from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.taller_tecnico.schemas import (
    TallerCreateRequest,
    TallerListItem,
    TallerListResponse,
    TallerTecnicoHealth,
    TallerUpdateRequest,
)
from app.modules.taller_tecnico.services import (
    actualizar_taller,
    crear_taller,
    desactivar_taller,
    listar_talleres,
    obtener_taller,
    reactivar_taller,
    taller_to_item,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import require_admin

router = APIRouter(prefix="/taller-tecnico", tags=["taller_tecnico"])
admin_talleres_router = APIRouter(prefix="/admin/talleres", tags=["admin-talleres"])


@router.get("/health", response_model=TallerTecnicoHealth)
def taller_tecnico_health() -> TallerTecnicoHealth:
    return TallerTecnicoHealth(modulo="taller_tecnico", status="ok")


@admin_talleres_router.get("", response_model=TallerListResponse)
def admin_listar_talleres(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
    activo: bool | None = Query(None, description="true=solo activos, false=solo inactivos, omitido=todos"),
) -> TallerListResponse:
    return listar_talleres(db, page=page, page_size=page_size, q=q, activo=activo)


@admin_talleres_router.get("/{taller_id}", response_model=TallerListItem)
def admin_obtener_taller(
    taller_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
) -> TallerListItem:
    t = obtener_taller(db, taller_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado.")
    return taller_to_item(t)


@admin_talleres_router.post("", response_model=TallerListItem, status_code=status.HTTP_201_CREATED)
def admin_crear_taller(
    body: TallerCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[Usuario, Depends(require_admin)],
) -> TallerListItem:
    return crear_taller(db, admin.id, body)


@admin_talleres_router.patch("/{taller_id}", response_model=TallerListItem)
def admin_actualizar_taller(
    taller_id: int,
    body: TallerUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
) -> TallerListItem:
    t = obtener_taller(db, taller_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado.")
    return actualizar_taller(db, t, body)


@admin_talleres_router.post("/{taller_id}/desactivar", response_model=TallerListItem)
def admin_desactivar_taller(
    taller_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
) -> TallerListItem:
    t = obtener_taller(db, taller_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado.")
    return desactivar_taller(db, t)


@admin_talleres_router.post("/{taller_id}/reactivar", response_model=TallerListItem)
def admin_reactivar_taller(
    taller_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
) -> TallerListItem:
    t = obtener_taller(db, taller_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado.")
    return reactivar_taller(db, t)
