"""API de vehículos: CRUD, bitácora y reglas de negocio (placa única, incidentes activos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.modules.incidentes_servicios.models import Incidente
from app.modules.sistema.logger import registrar_bitacora
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo
from app.modules.usuario_autenticacion.schemas import (
    VehiculoCreateRequest,
    VehiculoItem,
    VehiculoListResponse,
    VehiculoUpdateRequest,
)
from app.modules.usuario_autenticacion.services import get_current_user

vehiculos_router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

TERMINAL_ESTADOS_INCIDENTE = frozenset(
    {"cerrado", "finalizado", "cancelado", "resuelto", "completado"},
)


def _is_admin(user: Usuario) -> bool:
    return any(r.nombre == "Administrador" for r in user.roles)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _vehiculo_tiene_incidente_activo(db: Session, vehiculo_id: int) -> bool:
    estados = db.scalars(
        select(Incidente.estado).where(Incidente.id_vehiculo == vehiculo_id),
    ).all()
    for est in estados:
        if (est or "").strip().lower() not in TERMINAL_ESTADOS_INCIDENTE:
            return True
    return False


def _get_vehiculo_acceso(db: Session, vehiculo_id: int, user: Usuario) -> Vehiculo | None:
    v = db.execute(
        select(Vehiculo).options(selectinload(Vehiculo.usuario)).where(Vehiculo.id == vehiculo_id),
    ).scalar_one_or_none()
    if v is None:
        return None
    if _is_admin(user):
        return v
    if v.id_usuario == user.id:
        return v
    return None


def _to_item(v: Vehiculo, *, incluir_propietario: bool) -> VehiculoItem:
    pn = pe = None
    if incluir_propietario and v.usuario is not None:
        u = v.usuario
        pn = f"{u.nombre} {u.apellido}".strip()
        pe = u.email
    return VehiculoItem(
        id=v.id,
        id_usuario=v.id_usuario,
        placa=v.placa,
        marca=v.marca,
        modelo=v.modelo,
        anio=v.anio,
        color=v.color,
        tipo_seguro=v.tiposeguro,
        foto_frontal=v.fotofrontal,
        propietario_nombre=pn,
        propietario_email=pe,
    )


@vehiculos_router.get("", response_model=VehiculoListResponse)
def listar_vehiculos(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    id_usuario: int | None = Query(None, description="Solo administrador"),
) -> VehiculoListResponse:
    ip = _client_ip(request)
    admin = _is_admin(user)
    if admin:
        # id_usuario<=0 se ignora: evita ?id_usuario=0 que filtraría a nadie
        if id_usuario is not None and id_usuario > 0:
            count_stmt = select(func.count()).select_from(Vehiculo).where(Vehiculo.id_usuario == id_usuario)
            stmt = select(Vehiculo).options(selectinload(Vehiculo.usuario)).where(Vehiculo.id_usuario == id_usuario)
        else:
            count_stmt = select(func.count()).select_from(Vehiculo)
            stmt = select(Vehiculo).options(selectinload(Vehiculo.usuario))
    else:
        count_stmt = select(func.count()).select_from(Vehiculo).where(Vehiculo.id_usuario == user.id)
        stmt = select(Vehiculo).options(selectinload(Vehiculo.usuario)).where(Vehiculo.id_usuario == user.id)

    total = int(db.scalar(count_stmt) or 0)
    rows = (
        db.execute(
            stmt.order_by(Vehiculo.id.desc()).offset((page - 1) * page_size).limit(page_size),
        )
        .scalars()
        .all()
    )
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="vehiculos",
        accion="LISTAR_VEHICULOS",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    return VehiculoListResponse(
        items=[_to_item(v, incluir_propietario=admin) for v in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@vehiculos_router.post("", response_model=VehiculoItem, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    body: VehiculoCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VehiculoItem:
    ip = _client_ip(request)
    admin = _is_admin(user)
    if admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El administrador no registra vehículos; el alta la realiza el cliente.",
        )
    owner_id = user.id
    if body.id_usuario is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés asignar el vehículo a otro usuario")

    v = Vehiculo(
        id_usuario=owner_id,
        placa=body.placa,
        marca=body.marca.strip(),
        modelo=body.modelo.strip(),
        anio=body.anio,
        color=body.color.strip() if body.color else None,
        tiposeguro=body.tipo_seguro.strip() if body.tipo_seguro else None,
        fotofrontal=body.foto_frontal.strip() if body.foto_frontal else None,
    )
    db.add(v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="vehiculos",
            accion="CREAR_VEHICULO",
            ip=ip,
            resultado="PLACA_DUPLICADA",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Placa ya registrada") from None

    db.flush()
    v = db.execute(
        select(Vehiculo).options(selectinload(Vehiculo.usuario)).where(Vehiculo.id == v.id),
    ).scalar_one()
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="vehiculos",
        accion="CREAR_VEHICULO",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    return _to_item(v, incluir_propietario=admin)


@vehiculos_router.get("/{vehiculo_id}", response_model=VehiculoItem)
def obtener_vehiculo(
    vehiculo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VehiculoItem:
    ip = _client_ip(request)
    v = _get_vehiculo_acceso(db, vehiculo_id, user)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="vehiculos",
        accion="VER_VEHICULO",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    return _to_item(v, incluir_propietario=_is_admin(user))


@vehiculos_router.patch("/{vehiculo_id}", response_model=VehiculoItem)
def actualizar_vehiculo(
    vehiculo_id: int,
    body: VehiculoUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VehiculoItem:
    ip = _client_ip(request)
    admin = _is_admin(user)
    v = _get_vehiculo_acceso(db, vehiculo_id, user)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    raw = body.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")

    if "id_usuario" in raw:
        if not admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administrador reasigna propietario")
        nu = raw.pop("id_usuario")
        if nu is not None:
            if db.get(Usuario, nu) is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario no encontrado")
            v.id_usuario = nu
    if "placa" in raw and raw["placa"] is not None:
        v.placa = raw.pop("placa")
    if "marca" in raw:
        m = raw.pop("marca")
        v.marca = m.strip() if m else v.marca
    if "modelo" in raw:
        m = raw.pop("modelo")
        v.modelo = m.strip() if m else v.modelo
    if "anio" in raw and raw["anio"] is not None:
        v.anio = raw.pop("anio")
    if "color" in raw:
        c = raw.pop("color")
        v.color = c.strip() if c else None
    if "tipo_seguro" in raw:
        t = raw.pop("tipo_seguro")
        v.tiposeguro = t.strip() if t else None
    if "foto_frontal" in raw:
        f = raw.pop("foto_frontal")
        v.fotofrontal = f.strip() if f else None

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="vehiculos",
            accion="ACTUALIZAR_VEHICULO",
            ip=ip,
            resultado="PLACA_DUPLICADA",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Placa ya registrada") from None

    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="vehiculos",
        accion="ACTUALIZAR_VEHICULO",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    v = db.execute(
        select(Vehiculo).options(selectinload(Vehiculo.usuario)).where(Vehiculo.id == vehiculo_id),
    ).scalar_one()
    return _to_item(v, incluir_propietario=admin)


@vehiculos_router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo(
    vehiculo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    ip = _client_ip(request)
    v = _get_vehiculo_acceso(db, vehiculo_id, user)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    if _vehiculo_tiene_incidente_activo(db, vehiculo_id):
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="vehiculos",
            accion="ELIMINAR_VEHICULO",
            ip=ip,
            resultado="INCIDENTE_ACTIVO",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: el vehículo tiene un incidente activo.",
        )

    # FK incidente -> vehiculo es RESTRICT: quitar incidentes ya cerrados antes de borrar el vehículo
    db.execute(delete(Incidente).where(Incidente.id_vehiculo == vehiculo_id))
    db.delete(v)
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="vehiculos",
        accion="ELIMINAR_VEHICULO",
        ip=ip,
        resultado="OK",
    )
    db.commit()
