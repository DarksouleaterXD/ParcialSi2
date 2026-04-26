from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.pagos.schemas import PagoCreateRequest, PagoListResponse, PagoResponse, PagosHealth
from app.modules.pagos.services import listar_pagos_paginado, procesar_pago_incidente, crear_payment_intent, procesar_webhook
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import get_current_user

router = APIRouter(prefix="/pagos", tags=["pagos"])


@router.get("/health", response_model=PagosHealth)
def pagos_health() -> PagosHealth:
    return PagosHealth(modulo="pagos", status="stub")


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None

@router.post("/create-payment-intent/{incidente_id}")
def create_payment_intent(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return crear_payment_intent(db, current_user, incidente_id)

@router.post("/webhook")
async def webhook_pago(request: Request, db: Session = Depends(get_db)):
    return await procesar_webhook(request, db)

@router.post("/incidentes/{incidente_id}/procesar", response_model=PagoResponse)
def procesar_pago(
    incidente_id: int,
    payload: PagoCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> PagoResponse:
    out = procesar_pago_incidente(
        db,
        current_user,
        incidente_id,
        payload,
        client_ip=_client_ip(request),
    )
    return PagoResponse(**out)


@router.get("", response_model=PagoListResponse)
def listar_pagos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PagoListResponse:
    out = listar_pagos_paginado(
        db,
        current_user,
        page=page,
        page_size=page_size,
    )
    return PagoListResponse(**out)
