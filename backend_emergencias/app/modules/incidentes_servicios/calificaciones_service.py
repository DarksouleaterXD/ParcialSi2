from __future__ import annotations

import logging
from datetime import date, datetime, time

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.modules.incidentes_servicios.calificaciones_schemas import (
    CalificacionAdminFilters,
    CalificacionCreateRequest,
    CalificacionItemResponse,
    CalificacionListResponse,
    CalificacionListSummary,
    ClienteRef,
    IncidenteRef,
    PagoRef,
    ServicioRef,
    TallerRef,
    TecnicoRef,
)
from app.modules.incidentes_servicios.models import Calificacion, Incidente
from app.modules.pagos.models import Pago
from app.modules.sistema.bitacora_service import AUDIT_MODULE_INCIDENTES_SERVICIOS, registrar_bitacora
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo

logger = logging.getLogger(__name__)

_ESTADOS_CALIFICABLES = frozenset({"finalizado", "pagado", "completado", "cerrado", "resuelto"})
_PAGO_OK = frozenset({"pagado", "confirmado", "completado", "paid", "succeeded"})


def _rol_nombre_normalizado(rol: object) -> str:
    nombre = getattr(rol, "nombre", None) or ""
    return str(nombre).strip().lower()


def _is_admin(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) in ("administrador", "admin") for r in user.roles)


def _is_cliente(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) == "cliente" for r in user.roles)


def _estado_key(v: str | None) -> str:
    return (v or "").strip().lower().replace(" ", "_")


def _ilike_fragment_escaped(raw: str) -> str:
    t = raw.strip()
    escaped = t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _build_calificacion_item(
    *,
    cal: Calificacion,
    inc: Incidente,
    cli: Usuario,
    pago: Pago | None,
    tecnico_user: Usuario | None,
    tecnico_taller: Taller | None,
) -> CalificacionItemResponse:
    servicio_id = inc.id
    return CalificacionItemResponse(
        id=cal.id,
        servicio_id=servicio_id,
        incidente_id=inc.id,
        puntuacion=cal.puntuacion,
        comentario=cal.comentario,
        fecha=cal.fecha,
        cliente=ClienteRef(
            id=cli.id,
            nombre=cli.nombre,
            apellido=cli.apellido,
            email=cli.email,
        ),
        taller=TallerRef(id=tecnico_taller.id, nombre=tecnico_taller.nombre) if tecnico_taller is not None else None,
        tecnico=(
            TecnicoRef(id=tecnico_user.id, nombre=tecnico_user.nombre, apellido=tecnico_user.apellido)
            if tecnico_user is not None
            else None
        ),
        servicio=ServicioRef(id=servicio_id, estado=inc.estado or ""),
        incidente=IncidenteRef(id=inc.id, estado=inc.estado or "", tipo=inc.categoria_ia),
        pago=(
            PagoRef(
                id=pago.id,
                monto_total=float(pago.monto_total),
                estado=pago.estado,
            )
            if pago is not None
            else None
        ),
    )


def _get_tecnico_context(
    db: Session,
    tecnico_ids: set[int],
) -> tuple[dict[int, Usuario], dict[int, Taller]]:
    if not tecnico_ids:
        return {}, {}
    tech_rows = db.execute(select(Usuario).where(Usuario.id.in_(tecnico_ids))).scalars().all()
    tech_map = {u.id: u for u in tech_rows}
    taller_rows = db.execute(
        select(MecanicoTaller.id_usuario, Taller)
        .join(Taller, Taller.id == MecanicoTaller.id_taller)
        .where(MecanicoTaller.id_usuario.in_(tecnico_ids))
        .order_by(MecanicoTaller.id_usuario, Taller.id)
    ).all()
    taller_map: dict[int, Taller] = {}
    for tecnico_id, taller in taller_rows:
        taller_map.setdefault(int(tecnico_id), taller)
    return tech_map, taller_map


def create_calificacion_for_cliente(
    db: Session,
    *,
    incidente_id: int,
    body: CalificacionCreateRequest,
    current_user: Usuario,
    client_ip: str | None,
) -> CalificacionItemResponse:
    inc = db.execute(
        select(Incidente)
        .options(selectinload(Incidente.vehiculo))
        .where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")
    if not _is_cliente(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden calificar.")
    if inc.vehiculo.id_usuario != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para calificar este servicio.")
    if _estado_key(inc.estado) not in _ESTADOS_CALIFICABLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se puede calificar un servicio finalizado.")

    pago = db.execute(select(Pago).where(Pago.incidente_id == incidente_id)).scalar_one_or_none()
    if pago is not None and _estado_key(pago.estado) not in _PAGO_OK:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El pago asociado aún no está confirmado.")

    existing = db.execute(select(Calificacion).where(Calificacion.id_incidente == incidente_id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este servicio ya tiene una calificación.")

    row = Calificacion(
        id_incidente=incidente_id,
        puntuacion=body.puntuacion,
        comentario=body.comentario,
    )
    db.add(row)
    registrar_bitacora(
        db,
        id_usuario=current_user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion="CREAR_CALIFICACION",
        ip=client_ip,
        resultado=f"OK iid={incidente_id} pts={body.puntuacion}"[:50],
    )
    db.commit()
    db.refresh(row)

    tecnico_ids = {inc.tecnico_id} if inc.tecnico_id is not None else set()
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    return _build_calificacion_item(
        cal=row,
        inc=inc,
        cli=current_user,
        pago=pago,
        tecnico_user=tech_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
        tecnico_taller=taller_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
    )


def list_calificaciones_mias(
    db: Session,
    *,
    current_user: Usuario,
    page: int,
    page_size: int,
) -> CalificacionListResponse:
    if not _is_cliente(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden consultar sus calificaciones.")

    base = (
        select(Calificacion, Incidente, Usuario, Pago)
        .join(Incidente, Incidente.id == Calificacion.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .where(Usuario.id == current_user.id)
    )
    total = int(
        db.scalar(
            select(func.count(Calificacion.id))
            .select_from(Calificacion)
            .join(Incidente, Incidente.id == Calificacion.id_incidente)
            .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
            .where(Vehiculo.id_usuario == current_user.id),
        )
        or 0
    )
    rows = db.execute(
        base.order_by(Calificacion.fecha.desc(), Calificacion.id.desc()).offset((page - 1) * page_size).limit(page_size),
    ).all()
    tecnico_ids = {inc.tecnico_id for _, inc, _, _ in rows if inc.tecnico_id is not None}
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    items = [
        _build_calificacion_item(
            cal=cal,
            inc=inc,
            cli=cli,
            pago=pago,
            tecnico_user=tech_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
            tecnico_taller=taller_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
        )
        for cal, inc, cli, pago in rows
    ]
    return CalificacionListResponse(items=items, page=page, page_size=page_size, total=total)


def _build_admin_conditions(filters: CalificacionAdminFilters):
    conditions = []
    if filters.puntuacion is not None:
        conditions.append(Calificacion.puntuacion == filters.puntuacion)
    if filters.puntuacion_min is not None:
        conditions.append(Calificacion.puntuacion >= filters.puntuacion_min)
    if filters.puntuacion_max is not None:
        conditions.append(Calificacion.puntuacion <= filters.puntuacion_max)
    if filters.fecha_desde is not None:
        conditions.append(Calificacion.fecha >= datetime.combine(filters.fecha_desde, time.min))
    if filters.fecha_hasta is not None:
        conditions.append(Calificacion.fecha <= datetime.combine(filters.fecha_hasta, time.max))
    if filters.estado_servicio and filters.estado_servicio.strip():
        conditions.append(Incidente.estado == filters.estado_servicio.strip())
    if filters.cliente and filters.cliente.strip():
        term = _ilike_fragment_escaped(filters.cliente[:120])
        conditions.append(
            or_(
                Usuario.nombre.ilike(term, escape="\\"),
                Usuario.apellido.ilike(term, escape="\\"),
                Usuario.email.ilike(term, escape="\\"),
            ),
        )
    tecnico_alias = aliased(Usuario)
    if filters.tecnico and filters.tecnico.strip():
        term_t = _ilike_fragment_escaped(filters.tecnico[:120])
        conditions.append(
            or_(
                tecnico_alias.nombre.ilike(term_t, escape="\\"),
                tecnico_alias.apellido.ilike(term_t, escape="\\"),
            ),
        )
    if filters.taller and filters.taller.strip():
        term_w = _ilike_fragment_escaped(filters.taller[:120])
        conditions.append(
            select(MecanicoTaller.id_usuario)
            .join(Taller, Taller.id == MecanicoTaller.id_taller)
            .where(
                MecanicoTaller.id_usuario == Incidente.tecnico_id,
                Taller.nombre.ilike(term_w, escape="\\"),
            )
            .exists(),
        )
    return conditions, tecnico_alias


def list_calificaciones_admin(
    db: Session,
    *,
    current_user: Usuario,
    page: int,
    page_size: int,
    filters: CalificacionAdminFilters,
) -> CalificacionListResponse:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores.")
    conditions, tecnico_alias = _build_admin_conditions(filters)

    count_stmt = (
        select(func.count(Calificacion.id))
        .select_from(Calificacion)
        .join(Incidente, Incidente.id == Calificacion.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(tecnico_alias, tecnico_alias.id == Incidente.tecnico_id)
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int(db.scalar(count_stmt) or 0)

    summary_stmt = (
        select(
            func.coalesce(func.avg(Calificacion.puntuacion), 0.0).label("avg"),
            func.sum(case((Calificacion.puntuacion == 1, 1), else_=0)).label("c1"),
            func.sum(case((Calificacion.puntuacion == 2, 1), else_=0)).label("c2"),
            func.sum(case((Calificacion.puntuacion == 3, 1), else_=0)).label("c3"),
            func.sum(case((Calificacion.puntuacion == 4, 1), else_=0)).label("c4"),
            func.sum(case((Calificacion.puntuacion == 5, 1), else_=0)).label("c5"),
        )
        .select_from(Calificacion)
        .join(Incidente, Incidente.id == Calificacion.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(tecnico_alias, tecnico_alias.id == Incidente.tecnico_id)
    )
    if conditions:
        summary_stmt = summary_stmt.where(*conditions)
    avg, c1, c2, c3, c4, c5 = db.execute(summary_stmt).one()
    summary = CalificacionListSummary(
        promedio_puntuacion=float(avg or 0.0),
        cantidad_1=int(c1 or 0),
        cantidad_2=int(c2 or 0),
        cantidad_3=int(c3 or 0),
        cantidad_4=int(c4 or 0),
        cantidad_5=int(c5 or 0),
    )

    list_stmt = (
        select(Calificacion, Incidente, Usuario, Pago)
        .join(Incidente, Incidente.id == Calificacion.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .outerjoin(tecnico_alias, tecnico_alias.id == Incidente.tecnico_id)
    )
    if conditions:
        list_stmt = list_stmt.where(*conditions)
    rows = db.execute(
        list_stmt.order_by(Calificacion.fecha.desc(), Calificacion.id.desc()).offset((page - 1) * page_size).limit(page_size),
    ).all()

    tecnico_ids = {inc.tecnico_id for _, inc, _, _ in rows if inc.tecnico_id is not None}
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    items = [
        _build_calificacion_item(
            cal=cal,
            inc=inc,
            cli=cli,
            pago=pago,
            tecnico_user=tech_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
            tecnico_taller=taller_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
        )
        for cal, inc, cli, pago in rows
    ]
    return CalificacionListResponse(items=items, page=page, page_size=page_size, total=total, summary=summary)


def get_calificacion_admin_detail(
    db: Session,
    *,
    calificacion_id: int,
    current_user: Usuario,
) -> CalificacionItemResponse:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores.")
    row = db.execute(
        select(Calificacion, Incidente, Usuario, Pago)
        .join(Incidente, Incidente.id == Calificacion.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .where(Calificacion.id == calificacion_id),
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calificación no encontrada.")
    cal, inc, cli, pago = row
    tecnico_ids = {inc.tecnico_id} if inc.tecnico_id is not None else set()
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    return _build_calificacion_item(
        cal=cal,
        inc=inc,
        cli=cli,
        pago=pago,
        tecnico_user=tech_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
        tecnico_taller=taller_map.get(inc.tecnico_id) if inc.tecnico_id is not None else None,
    )
