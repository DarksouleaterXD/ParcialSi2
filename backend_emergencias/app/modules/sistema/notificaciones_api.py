"""CU-17: notificaciones in-app y registro de tokens FCM."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.sistema.models import Notificacion, NotificacionPushToken
from app.modules.sistema.schemas import (
    MarcarTodasLeidasResponse,
    NotificacionItem,
    NotificacionListResponse,
    NotificacionPatch,
    NoLeidasCount,
    PushTokenIn,
    PushTokenUnregisterIn,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import get_current_user

notificaciones_router = APIRouter(prefix="/notificaciones", tags=["sistema-notificaciones"])
MAX_LIST = 100


def _to_item(n: Notificacion) -> NotificacionItem:
    return NotificacionItem(
        id=int(n.id),
        titulo=n.titulo or "",
        mensaje=n.mensaje or "",
        leida=bool(n.leida),
        tipo=n.tipo,
        fecha_hora=n.fechahora,
    )


@notificaciones_router.get("", response_model=NotificacionListResponse)
def listar_notificaciones(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=MAX_LIST),
    solo_no_leidas: bool = Query(False, description="Solo leida=false"),
) -> NotificacionListResponse:
    base = select(Notificacion).where(Notificacion.id_usuario == user.id)
    if solo_no_leidas:
        base = base.where(Notificacion.leida.is_(False))
    count_q = select(func.count()).select_from(Notificacion).where(Notificacion.id_usuario == user.id)
    if solo_no_leidas:
        count_q = count_q.where(Notificacion.leida.is_(False))
    total = int(db.execute(count_q).scalar_one() or 0)
    rows = (
        db.execute(
            base.order_by(Notificacion.fechahora.desc().nulls_last(), Notificacion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size),
        )
        .scalars()
        .all()
    )
    return NotificacionListResponse(
        items=[_to_item(n) for n in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@notificaciones_router.get("/no-leidas", response_model=NoLeidasCount)
def notificaciones_no_leidas(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> NoLeidasCount:
    c = int(
        db.execute(
            select(func.count(Notificacion.id)).where(
                Notificacion.id_usuario == user.id,
                Notificacion.leida.is_(False),
            )
        ).scalar_one()
    )
    return NoLeidasCount(count=c)


@notificaciones_router.patch("/{notif_id}", response_model=NotificacionItem)
def marcar_una(
    notif_id: int,
    body: NotificacionPatch,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> NotificacionItem:
    n = db.get(Notificacion, notif_id)
    if n is None or n.id_usuario != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    n.leida = bool(body.leida)
    db.add(n)
    db.commit()
    db.refresh(n)
    return _to_item(n)


@notificaciones_router.post("/marcar-todas-leidas", response_model=MarcarTodasLeidasResponse)
def marcar_todas(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> MarcarTodasLeidasResponse:
    r = db.execute(
        update(Notificacion)
        .where(Notificacion.id_usuario == user.id, Notificacion.leida.is_(False))
        .values(leida=True)
    )
    n = r.rowcount or 0
    db.commit()
    return MarcarTodasLeidasResponse(updated=n)


@notificaciones_router.post("/push-token", status_code=status.HTTP_204_NO_CONTENT)
def registrar_push_token(
    body: PushTokenIn,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    tok = (body.token or "").strip()
    if not tok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Token vacío")
    plat = (body.plataforma or "desconocida").strip()[:32]
    existing = db.execute(
        select(NotificacionPushToken).where(
            NotificacionPushToken.id_usuario == user.id,
            NotificacionPushToken.token == tok,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.plataforma = plat
        db.add(existing)
    else:
        db.add(NotificacionPushToken(id_usuario=user.id, token=tok, plataforma=plat))
    db.commit()
    return None


@notificaciones_router.post("/push-token/desregistrar", status_code=status.HTTP_204_NO_CONTENT)
def desregistrar_push_token(
    body: PushTokenUnregisterIn,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    tok = (body.token or "").strip()
    if not tok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Token vacío")
    db.execute(
        delete(NotificacionPushToken).where(
            NotificacionPushToken.id_usuario == user.id,
            NotificacionPushToken.token == tok,
        )
    )
    db.commit()
    return None
