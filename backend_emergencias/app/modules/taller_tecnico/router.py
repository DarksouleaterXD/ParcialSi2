from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.taller_tecnico.schemas import (
    TallerCreateRequest,
    TallerListItem,
    TallerListResponse,
    TallerTecnicoHealth,
    TallerUpdateRequest,
    TechnicianCreateRequest,
    TechnicianCreateResponse,
    TechnicianListResponse,
    TechnicianListItem,
    TechnicianUpdateRequest,
)
from app.modules.taller_tecnico.technicians_service import (
    technician_create,
    technician_deactivate,
    technician_list,
    technician_update,
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


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


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


@admin_talleres_router.get("/{taller_id}/technicians", response_model=TechnicianListResponse)
def admin_listar_tecnicos(
    taller_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[Usuario, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TechnicianListResponse:
    return technician_list(db, taller_id=taller_id, page=page, page_size=page_size)


@admin_talleres_router.post(
    "/{taller_id}/technicians",
    response_model=TechnicianCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_crear_tecnico(
    taller_id: int,
    body: TechnicianCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[Usuario, Depends(require_admin)],
) -> TechnicianCreateResponse:
    return technician_create(
        db,
        admin_id=admin.id,
        taller_id=taller_id,
        body=body,
        client_ip=_client_ip(request),
        background_tasks=background_tasks,
    )


@admin_talleres_router.patch("/{taller_id}/technicians/{user_id}", response_model=TechnicianListItem)
def admin_actualizar_tecnico(
    taller_id: int,
    user_id: int,
    body: TechnicianUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[Usuario, Depends(require_admin)],
) -> TechnicianListItem:
    return technician_update(
        db,
        admin_id=admin.id,
        taller_id=taller_id,
        user_id=user_id,
        body=body,
        client_ip=_client_ip(request),
    )


@admin_talleres_router.post(
    "/{taller_id}/technicians/{user_id}/desactivar",
    response_model=TechnicianListItem,
)
def admin_desactivar_tecnico(
    taller_id: int,
    user_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[Usuario, Depends(require_admin)],
) -> TechnicianListItem:
    return technician_deactivate(
        db,
        admin_id=admin.id,
        taller_id=taller_id,
        user_id=user_id,
        client_ip=_client_ip(request),
    )


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
