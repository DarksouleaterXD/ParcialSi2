from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.incidentes_servicios.calificaciones_schemas import (
    CalificacionAdminFilters,
    CalificacionCreateRequest,
    CalificacionItemResponse,
    CalificacionListResponse,
)
from app.modules.incidentes_servicios.calificaciones_service import (
    create_calificacion_for_cliente,
    get_calificacion_admin_detail,
    list_calificaciones_admin,
    list_calificaciones_mias,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import get_current_user

router = APIRouter(prefix="/incidentes-servicios", tags=["incidentes_servicios"])
admin_router = APIRouter(prefix="/admin/incidentes-servicios", tags=["incidentes_servicios"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.post("/{incidente_id}/calificacion", response_model=CalificacionItemResponse, summary="Calificar servicio (cliente)")
def create_calificacion(
    incidente_id: int,
    body: CalificacionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> CalificacionItemResponse:
    return create_calificacion_for_cliente(
        db,
        incidente_id=incidente_id,
        body=body,
        current_user=user,
        client_ip=_client_ip(request),
    )


@router.get("/calificaciones/mis", response_model=CalificacionListResponse, summary="Mis calificaciones (cliente)")
def list_mis_calificaciones(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> CalificacionListResponse:
    return list_calificaciones_mias(db, current_user=user, page=page, page_size=page_size)


@admin_router.get("/calificaciones", response_model=CalificacionListResponse, summary="Listar calificaciones (admin)")
def list_calificaciones_admin_endpoint(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    cliente: str | None = Query(default=None, max_length=120),
    taller: str | None = Query(default=None, max_length=120),
    tecnico: str | None = Query(default=None, max_length=120),
    puntuacion: Annotated[int | None, Query(ge=1, le=5)] = None,
    puntuacion_min: Annotated[int | None, Query(ge=1, le=5)] = None,
    puntuacion_max: Annotated[int | None, Query(ge=1, le=5)] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    estado_servicio: str | None = Query(default=None, max_length=50),
) -> CalificacionListResponse:
    filters = CalificacionAdminFilters(
        cliente=cliente,
        taller=taller,
        tecnico=tecnico,
        puntuacion=puntuacion,
        puntuacion_min=puntuacion_min,
        puntuacion_max=puntuacion_max,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado_servicio=estado_servicio,
    )
    return list_calificaciones_admin(
        db,
        current_user=user,
        page=page,
        page_size=page_size,
        filters=filters,
    )


@admin_router.get(
    "/calificaciones/{calificacion_id}",
    response_model=CalificacionItemResponse,
    summary="Detalle de calificación (admin)",
)
def get_calificacion_admin_endpoint(
    calificacion_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> CalificacionItemResponse:
    return get_calificacion_admin_detail(db, calificacion_id=calificacion_id, current_user=user)
