from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.sistema.models import Bitacora
from app.modules.sistema.schemas import (
    BitacoraDetailResponse,
    BitacoraListItem,
    BitacoraListResponse,
    BitacoraUsuarioRef,
    ModuloSistemaHealth,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import require_admin

router = APIRouter(prefix="/sistema", tags=["sistema"])
bitacora_router = APIRouter(prefix="/admin/bitacora", tags=["admin-sistema"])


def _bitacora_filter_clauses(
    *,
    fecha: date | None,
    modulo: str | None,
    accion: str | None,
    usuario: str | None,
) -> list:
    clauses: list = []
    if fecha is not None:
        desde = datetime.combine(fecha, time.min)
        hasta = desde + timedelta(days=1)
        clauses.append(and_(Bitacora.fechahora >= desde, Bitacora.fechahora < hasta))

    if modulo and modulo.strip():
        clauses.append(Bitacora.modulo == modulo.strip())

    if accion and accion.strip():
        clauses.append(Bitacora.accion == accion.strip())

    if usuario and usuario.strip():
        term = usuario.strip()
        cond = or_(
            Usuario.nombre.ilike(f"%{term}%"),
            Usuario.apellido.ilike(f"%{term}%"),
            Usuario.email.ilike(f"%{term}%"),
        )
        if term.isdigit():
            cond = or_(cond, Usuario.id == int(term))
        clauses.append(cond)

    return clauses


def _to_item(bitacora: Bitacora, usuario: Usuario) -> BitacoraListItem:
    return BitacoraListItem(
        id=bitacora.id,
        id_usuario=bitacora.id_usuario,
        modulo=bitacora.modulo,
        accion=bitacora.accion,
        ip_origen=bitacora.iporigen,
        resultado=bitacora.resultado,
        fecha_hora=bitacora.fechahora,
        usuario=BitacoraUsuarioRef(
            id=usuario.id,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            email=usuario.email,
        ),
    )


@router.get("/health", response_model=ModuloSistemaHealth)
def sistema_health() -> ModuloSistemaHealth:
    return ModuloSistemaHealth(modulo="sistema", status="ok")


@bitacora_router.get("", response_model=BitacoraListResponse)
def list_bitacora(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_admin),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    fecha: Annotated[date | None, Query(description="Fecha exacta YYYY-MM-DD")] = None,
    modulo: Annotated[str | None, Query(description="Filtro exacto por módulo (columna modulo)")] = None,
    usuario: Annotated[str | None, Query(description="Filtro por nombre, apellido, email o ID")] = None,
    accion: Annotated[str | None, Query(description="Filtro exacto por acción (columna accion)")] = None,
) -> BitacoraListResponse:
    clauses = _bitacora_filter_clauses(fecha=fecha, modulo=modulo, accion=accion, usuario=usuario)
    join_on = Usuario.id == Bitacora.id_usuario

    stmt = select(Bitacora, Usuario).join(Usuario, join_on)
    for c in clauses:
        stmt = stmt.where(c)

    count_stmt = select(func.count(Bitacora.id)).select_from(Bitacora).join(Usuario, join_on)
    for c in clauses:
        count_stmt = count_stmt.where(c)

    total = int(db.execute(count_stmt).scalar_one())
    rows = db.execute(
        stmt.order_by(Bitacora.fechahora.desc(), Bitacora.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size),
    ).all()

    return BitacoraListResponse(
        items=[_to_item(bit, usr) for bit, usr in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@bitacora_router.get("/{bitacora_id}", response_model=BitacoraDetailResponse)
def get_bitacora_detail(
    bitacora_id: int,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_admin),
) -> BitacoraDetailResponse:
    row = db.execute(
        select(Bitacora, Usuario)
        .join(Usuario, Usuario.id == Bitacora.id_usuario)
        .where(Bitacora.id == bitacora_id),
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de bitácora no encontrado")
    bitacora, usuario = row
    item = _to_item(bitacora, usuario)
    return BitacoraDetailResponse(**item.model_dump())
