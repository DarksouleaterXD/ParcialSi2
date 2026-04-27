"""Lógica de negocio — técnicos (mecánicos) asignados a un taller."""

from __future__ import annotations

import secrets

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, password_policy_violation
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_TECHNICIAN_CREATE,
    AUDIT_ACTION_TECHNICIAN_DEACTIVATE,
    AUDIT_ACTION_TECHNICIAN_UPDATE,
    AUDIT_MODULE_TALLER_TECHNICO,
    registrar_bitacora,
)
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.taller_tecnico.schemas import (
    TechnicianCreateRequest,
    TechnicianCreateResponse,
    TechnicianListItem,
    TechnicianListResponse,
    TechnicianUpdateRequest,
)
from app.modules.usuario_autenticacion.models import Rol, Usuario, usuario_rol
from app.modules.usuario_autenticacion.services import enviar_credenciales_nuevo_usuario_sync

ROL_TECNICO = "Tecnico"


def _tecnico_rol_id(db: Session) -> int:
    rid = db.execute(select(Rol.id).where(Rol.nombre == ROL_TECNICO)).scalar_one_or_none()
    if rid is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rol de técnico no configurado en el sistema.",
        )
    return int(rid)


def _get_taller_or_404(db: Session, taller_id: int) -> Taller:
    t = db.get(Taller, taller_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado.")
    return t


def _require_taller_disponible(db: Session, taller_id: int) -> Taller:
    t = _get_taller_or_404(db, taller_id)
    if not bool(t.disponibilidad):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El taller no está disponible para asignaciones.",
        )
    return t


def _audit_outcome(*, target_id: int, workshop_id: int, specialty: str | None = None) -> str:
    base = f"t={target_id}:w={workshop_id}"
    if specialty:
        extra = f":s={specialty}"[:20]
        return (base + extra)[:50]
    return base[:50]


def _to_list_item(u: Usuario, taller_id: int, especialidad: str | None) -> TechnicianListItem:
    return TechnicianListItem(
        id=u.id,
        nombre=u.nombre,
        apellido=u.apellido,
        email=u.email,
        telefono=u.telefono,
        especialidad=especialidad,
        taller_id=taller_id,
        estado=u.estado,
    )


def technician_list(
    db: Session,
    *,
    taller_id: int,
    page: int,
    page_size: int,
) -> TechnicianListResponse:
    _get_taller_or_404(db, taller_id)
    rid_tecnico = _tecnico_rol_id(db)
    base_join = (
        select(Usuario, MecanicoTaller.especialidad)
        .join(MecanicoTaller, MecanicoTaller.id_usuario == Usuario.id)
        .join(usuario_rol, usuario_rol.c.id_usuario == Usuario.id)
        .where(
            MecanicoTaller.id_taller == taller_id,
            usuario_rol.c.id_rol == rid_tecnico,
        )
    )
    count_stmt = (
        select(func.count())
        .select_from(Usuario)
        .join(MecanicoTaller, MecanicoTaller.id_usuario == Usuario.id)
        .join(usuario_rol, usuario_rol.c.id_usuario == Usuario.id)
        .where(
            MecanicoTaller.id_taller == taller_id,
            usuario_rol.c.id_rol == rid_tecnico,
        )
    )
    total = int(db.execute(count_stmt).scalar_one())
    stmt = (
        base_join.order_by(Usuario.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = db.execute(stmt).all()
    items = [_to_list_item(u, taller_id, esp) for u, esp in rows]
    return TechnicianListResponse(items=items, total=total, page=page, page_size=page_size)


def technician_create(
    db: Session,
    *,
    admin_id: int,
    taller_id: int,
    body: TechnicianCreateRequest,
    client_ip: str | None,
    background_tasks: BackgroundTasks,
) -> TechnicianCreateResponse:
    _require_taller_disponible(db, taller_id)
    rid = _tecnico_rol_id(db)
    rol = db.get(Rol, rid)
    if rol is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rol de técnico no disponible.")

    email_norm = str(body.email).strip().lower()
    pw = (body.password or "").strip()
    pwc = (body.password_confirmacion or "").strip()
    enviar_correo = True
    if pw or pwc:
        if not pw or not pwc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Completá contraseña y confirmación.",
            )
        if pw != pwc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las contraseñas no coinciden.",
            )
        policy_msg = password_policy_violation(pw)
        if policy_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=policy_msg,
            )
        password_plano = pw
        enviar_correo = False
    else:
        password_plano = secrets.token_urlsafe(12)
    u = Usuario(
        nombre=body.nombre.strip(),
        apellido=body.apellido.strip(),
        email=email_norm,
        passwordhash=hash_password(password_plano),
        telefono=body.telefono.strip() if body.telefono else None,
        estado="Activo",
    )
    u.roles.append(rol)
    db.add(u)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email.",
        ) from None

    db.add(MecanicoTaller(id_usuario=u.id, id_taller=taller_id, especialidad=body.especialidad))
    registrar_bitacora(
        db,
        id_usuario=admin_id,
        modulo=AUDIT_MODULE_TALLER_TECHNICO,
        accion=AUDIT_ACTION_TECHNICIAN_CREATE,
        ip=client_ip,
        resultado=_audit_outcome(target_id=u.id, workshop_id=taller_id, specialty=body.especialidad),
    )
    db.commit()
    db.refresh(u)

    nombre = f"{u.nombre} {u.apellido}".strip()
    if enviar_correo:
        background_tasks.add_task(
            enviar_credenciales_nuevo_usuario_sync,
            destino=u.email,
            password_plano=password_plano,
            nombre=nombre,
        )
    return TechnicianCreateResponse(
        id=u.id,
        nombre=u.nombre,
        apellido=u.apellido,
        email=u.email,
        telefono=u.telefono,
        especialidad=body.especialidad,
        taller_id=taller_id,
        estado=u.estado,
        password_generada=password_plano,
    )


def technician_update(
    db: Session,
    *,
    admin_id: int,
    taller_id: int,
    user_id: int,
    body: TechnicianUpdateRequest,
    client_ip: str | None,
) -> TechnicianListItem:
    _get_taller_or_404(db, taller_id)
    rid_tecnico = _tecnico_rol_id(db)
    u = db.execute(
        select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id),
    ).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Técnico no encontrado.")
    if not any(r.id == rid_tecnico for r in u.roles):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Técnico no encontrado.")

    mt = db.get(MecanicoTaller, (user_id, taller_id))
    if mt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El técnico no está asignado a este taller.",
        )

    raw = body.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar.")

    if "nombre" in raw and raw["nombre"] is not None:
        u.nombre = str(raw["nombre"]).strip()
    if "apellido" in raw and raw["apellido"] is not None:
        u.apellido = str(raw["apellido"]).strip()
    if "email" in raw and raw["email"] is not None:
        u.email = str(raw["email"]).strip().lower()
    if "telefono" in raw:
        tel = raw["telefono"]
        u.telefono = str(tel).strip() if tel is not None and str(tel).strip() else None
    if "especialidad" in raw and raw["especialidad"] is not None:
        mt.especialidad = raw["especialidad"]

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email.",
        ) from None

    registrar_bitacora(
        db,
        id_usuario=admin_id,
        modulo=AUDIT_MODULE_TALLER_TECHNICO,
        accion=AUDIT_ACTION_TECHNICIAN_UPDATE,
        ip=client_ip,
        resultado=_audit_outcome(target_id=user_id, workshop_id=taller_id, specialty=mt.especialidad),
    )
    db.commit()
    db.refresh(u)
    return _to_list_item(u, taller_id, mt.especialidad)


def technician_deactivate(
    db: Session,
    *,
    admin_id: int,
    taller_id: int,
    user_id: int,
    client_ip: str | None,
) -> TechnicianListItem:
    _get_taller_or_404(db, taller_id)
    rid_tecnico = _tecnico_rol_id(db)
    u = db.execute(
        select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id),
    ).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Técnico no encontrado.")
    if not any(r.id == rid_tecnico for r in u.roles):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Técnico no encontrado.")

    mt = db.get(MecanicoTaller, (user_id, taller_id))
    if mt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El técnico no está asignado a este taller.",
        )

    u.estado = "Inactivo"
    registrar_bitacora(
        db,
        id_usuario=admin_id,
        modulo=AUDIT_MODULE_TALLER_TECHNICO,
        accion=AUDIT_ACTION_TECHNICIAN_DEACTIVATE,
        ip=client_ip,
        resultado=_audit_outcome(target_id=user_id, workshop_id=taller_id, specialty=mt.especialidad),
    )
    db.commit()
    db.refresh(u)
    return _to_list_item(u, taller_id, mt.especialidad)
