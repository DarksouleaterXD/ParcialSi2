"""Lógica de procesamiento de pagos."""

from __future__ import annotations

import json

import stripe
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.incidentes_servicios.models import Incidente
from app.modules.pagos.models import Pago
from app.modules.pagos.schemas import PagoCreateRequest
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_PAGO_PROCESADO,
    AUDIT_MODULE_PAGOS,
    registrar_bitacora,
)
from app.modules.usuario_autenticacion.models import Usuario

stripe.api_key = settings.stripe_secret_key


def _rol_nombre_normalizado(rol: object) -> str:
    nombre = getattr(rol, "nombre", None) or ""
    return str(nombre).strip().lower()


def _is_cliente(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) == "cliente" for r in user.roles)


def _is_tecnico(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) == "tecnico" for r in user.roles)


def _is_admin(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) in ("administrador", "admin") for r in user.roles)


def _to_money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_response_payload(pago: Pago) -> dict:
    return {
        "id": pago.id,
        "incidente_id": pago.incidente_id,
        "cliente_id": pago.cliente_id,
        "tecnico_id": pago.tecnico_id,
        "monto_total": float(pago.monto_total),
        "monto_taller": float(pago.monto_taller),
        "comision_plataforma": float(pago.comision_plataforma),
        "metodo_pago": pago.metodo_pago,
        "estado": pago.estado,
        "created_at": pago.created_at,
    }


def procesar_pago_incidente(
    db: Session,
    current_user: Usuario,
    incidente_id: int,
    payload: PagoCreateRequest,
    *,
    client_ip: str | None,
) -> dict:
    incidente = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if incidente is None or incidente.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")

    if not _is_cliente(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden procesar pagos.",
        )
    if incidente.vehiculo.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para pagar este incidente.",
        )

    estado = (incidente.estado or "").strip().lower()
    if estado == "pagado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este incidente ya fue pagado.",
        )
    if estado != "finalizado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede pagar un incidente finalizado.",
        )

    existing = db.execute(select(Pago).where(Pago.incidente_id == incidente_id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un pago para este incidente.",
        )

    if incidente.tecnico_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El incidente no tiene técnico asignado para procesar el pago.",
        )

    monto_total = _to_money(payload.monto_total)
    comision = _to_money(monto_total * Decimal("0.10"))
    monto_taller = _to_money(monto_total - comision)

    pago = Pago(
        incidente_id=incidente.id,
        cliente_id=current_user.id,
        tecnico_id=incidente.tecnico_id,
        monto_total=monto_total,
        monto_taller=monto_taller,
        comision_plataforma=comision,
        metodo_pago=payload.metodo_pago,
        estado="COMPLETADO",
    )
    db.add(pago)
    incidente.estado = "Pagado"
    registrar_bitacora(
        db,
        id_usuario=current_user.id,
        modulo=AUDIT_MODULE_PAGOS,
        accion=AUDIT_ACTION_PAGO_PROCESADO,
        ip=client_ip,
        resultado=f"OK iid={incidente.id} total={monto_total} com={comision}"[:50],
    )
    db.commit()
    db.refresh(pago)
    return _to_response_payload(pago)


def listar_pagos_paginado(
    db: Session,
    current_user: Usuario,
    *,
    page: int,
    page_size: int,
) -> dict:
    if _is_admin(current_user):
        scope = "all"
    elif _is_tecnico(current_user):
        scope = "tecnico"
    elif _is_cliente(current_user):
        scope = "cliente"
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para listar pagos.",
        )

    conditions = []
    if scope == "tecnico":
        conditions.append(Pago.tecnico_id == current_user.id)
    elif scope == "cliente":
        conditions.append(Pago.cliente_id == current_user.id)

    count_stmt = select(func.count(Pago.id)).select_from(Pago)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int(db.scalar(count_stmt) or 0)

    list_stmt = select(Pago)
    if conditions:
        list_stmt = list_stmt.where(*conditions)
    list_stmt = list_stmt.order_by(Pago.created_at.desc(), Pago.id.desc()).offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(list_stmt).scalars().all()
    items = [_to_response_payload(p) for p in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
def crear_payment_intent(db: Session, current_user: Usuario, incidente_id: int) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe no está configurado.",
        )

    incidente = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if incidente is None or incidente.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")
    if not _is_cliente(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden procesar pagos.")
    if incidente.vehiculo.id_usuario != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para pagar este incidente.")

    estado = (incidente.estado or "").strip().lower()
    if estado == "pagado":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este incidente ya fue pagado.")
    if estado != "finalizado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede iniciar el pago cuando el incidente está finalizado.",
        )

    existing = db.execute(select(Pago).where(Pago.incidente_id == incidente_id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un pago para este incidente.")

    monto_total = Decimal("50.00")
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(monto_total * 100),
            currency="usd",
            metadata={"incidente_id": str(incidente_id)},
        )
        return {"client_secret": intent.client_secret, "monto_total": float(monto_total)}
    except stripe.error.StripeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo crear el pago en Stripe.",
        )


async def procesar_webhook(request: Request, db: Session) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Firma de webhook inválida.")
    try:
        stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Firma inválida.")

    body = json.loads(payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload)
    if body.get("type") == "payment_intent.succeeded":
        intent = body.get("data", {}).get("object") or {}
        meta = intent.get("metadata") or {}
        incidente_id_raw = meta.get("incidente_id") if isinstance(meta, dict) else None
        if incidente_id_raw is None:
            return {"status": "success"}
        try:
            incidente_id = int(str(incidente_id_raw))
        except ValueError:
            return {"status": "success"}

        incidente = db.execute(
            select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
        ).scalar_one_or_none()
        if incidente is None or incidente.vehiculo is None:
            return {"status": "success"}
        if (incidente.estado or "").strip().lower() == "pagado":
            return {"status": "success"}

        existing = db.execute(select(Pago).where(Pago.incidente_id == incidente_id)).scalar_one_or_none()
        if existing is not None:
            incidente.estado = "Pagado"
            db.commit()
            return {"status": "success"}

        monto_total = Decimal(str(intent.get("amount", 0))) / 100
        comision = _to_money(monto_total * Decimal("0.10"))
        monto_taller = _to_money(monto_total - comision)

        if incidente.tecnico_id is None:
            return {"status": "success"}
        pago = Pago(
            incidente_id=incidente.id,
            cliente_id=incidente.vehiculo.id_usuario,
            tecnico_id=incidente.tecnico_id,
            monto_total=monto_total,
            monto_taller=monto_taller,
            comision_plataforma=comision,
            metodo_pago="STRIPE",
            estado="COMPLETADO",
        )
        db.add(pago)
        incidente.estado = "Pagado"
        registrar_bitacora(
            db,
            id_usuario=incidente.vehiculo.id_usuario,
            modulo=AUDIT_MODULE_PAGOS,
            accion=AUDIT_ACTION_PAGO_PROCESADO,
            ip=None,
            resultado=f"Stripe iid={incidente.id} total={monto_total} com={comision}"[:50],
        )
        db.commit()

    return {"status": "success"}
