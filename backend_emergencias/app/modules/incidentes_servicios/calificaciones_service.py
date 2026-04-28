from __future__ import annotations

import logging
from datetime import date, datetime, time

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased, selectinload

from app.modules.incidentes_servicios.calificaciones_schemas import (
    CalificacionAdminFilters,
    CalificacionCreateRequest,
    CalificacionCreateResponse,
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
from app.modules.incidentes_servicios.models import AsignacionServicio, Calificacion, Incidente
from app.modules.pagos.models import Pago
from app.modules.sistema.bitacora_service import AUDIT_MODULE_INCIDENTES_SERVICIOS, registrar_bitacora
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo

logger = logging.getLogger(__name__)

_FINAL_ESTADOS_ASIGNACION = frozenset(
    {
        "finalizado",
        "finalizada",
        "completado",
        "cerrado",
        "resuelto",
        "pagado",
        "terminado",
        "terminada",
    },
)


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


def _txt(v: object | None) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _asignacion_finalizada(asi: AsignacionServicio) -> bool:
    if asi.fecha_fin is not None:
        return True
    return _estado_key(asi.estado) in _FINAL_ESTADOS_ASIGNACION


def _latest_asignacion(db: Session, incidente_id: int) -> AsignacionServicio | None:
    return (
        db.scalars(
            select(AsignacionServicio)
            .where(AsignacionServicio.id_incidente == incidente_id)
            .order_by(AsignacionServicio.id.desc()),
        ).first()
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
        .order_by(MecanicoTaller.id_usuario, Taller.id),
    ).all()
    taller_map: dict[int, Taller] = {}
    for tecnico_id, taller in taller_rows:
        taller_map.setdefault(int(tecnico_id), taller)
    return tech_map, taller_map


def _build_calificacion_item(
    *,
    cal: Calificacion,
    inc: Incidente,
    asignacion: AsignacionServicio,
    cli: Usuario,
    pago: Pago | None,
    tecnico_user: Usuario | None,
    tecnico_taller: Taller | None,
) -> CalificacionItemResponse:
    servicio_id = inc.id
    monto_val = 0.0
    if pago is not None and pago.monto_total is not None:
        monto_val = float(pago.monto_total)
    pago_estado = _txt(pago.estado) if pago is not None else ""
    return CalificacionItemResponse(
        id=int(cal.id),
        id_asignacion=int(asignacion.id),
        servicio_id=servicio_id,
        incidente_id=inc.id,
        puntuacion=int(cal.puntuacion),
        comentario=cal.comentario,
        fecha=cal.fecha,
        cliente=ClienteRef(
            id=int(cli.id),
            nombre=_txt(cli.nombre) or "—",
            apellido=_txt(cli.apellido) or "—",
            email=_txt(cli.email) or None,
        ),
        taller=(
            TallerRef(id=int(tecnico_taller.id), nombre=_txt(tecnico_taller.nombre) or "—")
            if tecnico_taller is not None
            else None
        ),
        tecnico=(
            TecnicoRef(
                id=int(tecnico_user.id),
                nombre=_txt(tecnico_user.nombre) or "—",
                apellido=_txt(tecnico_user.apellido) or "—",
            )
            if tecnico_user is not None
            else None
        ),
        servicio=ServicioRef(id=servicio_id, estado=_txt(inc.estado)),
        incidente=IncidenteRef(
            id=inc.id,
            estado=_txt(inc.estado),
            tipo=(_txt(inc.categoria_ia) or None),
        ),
        pago=(
            PagoRef(
                id=int(pago.id),
                monto_total=monto_val,
                estado=pago_estado or "—",
            )
            if pago is not None
            else None
        ),
    )


def create_calificacion_for_cliente(
    db: Session,
    *,
    incidente_id: int,
    body: CalificacionCreateRequest,
    current_user: Usuario,
    client_ip: str | None,
) -> CalificacionCreateResponse:
    try:
        return _create_calificacion_for_cliente_impl(
            db,
            incidente_id=incidente_id,
            body=body,
            current_user=current_user,
            client_ip=client_ip,
        )
    except HTTPException:
        raise
    except ProgrammingError as exc:
        logger.exception("Calificación: ProgrammingError incidente_id=%s", incidente_id)
        hint = getattr(exc, "orig", None) or exc
        hint_s = str(hint).strip()
        if len(hint_s) > 350:
            hint_s = hint_s[:350] + "…"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error SQL al registrar la calificación. Detalle: {hint_s}",
        ) from exc
    except Exception:
        logger.exception("Error inesperado al crear calificación (incidente_id=%s)", incidente_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la calificación. Intentá de nuevo en unos segundos.",
        ) from None


def _create_calificacion_for_cliente_impl(
    db: Session,
    *,
    incidente_id: int,
    body: CalificacionCreateRequest,
    current_user: Usuario,
    client_ip: str | None,
) -> CalificacionCreateResponse:
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para calificar este servicio.",
        )

    asignacion = _latest_asignacion(db, incidente_id)
    if asignacion is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe una asignación de servicio para este incidente.",
        )
    if not _asignacion_finalizada(asignacion):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio debe estar finalizado para poder calificar.",
        )

    existing = (
        db.scalars(
            select(Calificacion)
            .where(Calificacion.id_asignacion == asignacion.id)
            .order_by(Calificacion.id.desc()),
        ).first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este servicio ya fue calificado.",
        )

    row = Calificacion(
        id_asignacion=asignacion.id,
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
        resultado=f"OK aid={asignacion.id} pts={body.puntuacion}"[:50],
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.exception("Calificacion integrity error (duplicate or FK)")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este servicio ya fue calificado.",
        ) from None
    except ProgrammingError:
        db.rollback()
        logger.exception("Calificacion programming error on commit")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Esquema de base de datos incompatible con esta versión del servidor.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Calificacion SQLAlchemyError on commit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar la calificación.",
        ) from None

    db.refresh(row)

    inc_after = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc_after is None:
        inc_after = inc
    asignacion_after = db.get(AsignacionServicio, asignacion.id)
    if asignacion_after is None:
        asignacion_after = asignacion

    pago_after = (
        db.scalars(select(Pago).where(Pago.incidente_id == incidente_id).order_by(Pago.id.desc())).first()
    )

    cli = db.get(Usuario, current_user.id)
    if cli is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")

    mid = asignacion_after.id_mecanico
    tecnico_ids = {mid} if mid is not None else set()
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    taller_direct = db.get(Taller, asignacion_after.id_taller)
    if taller_direct is not None:
        taller_map[mid] = taller_direct

    try:
        base = _build_calificacion_item(
            cal=row,
            inc=inc_after,
            asignacion=asignacion_after,
            cli=cli,
            pago=pago_after,
            tecnico_user=tech_map.get(mid) if mid is not None else None,
            tecnico_taller=taller_map.get(mid) if mid is not None else None,
        )
        return CalificacionCreateResponse(**base.model_dump(), mensaje="Calificación registrada correctamente.")
    except ValidationError:
        logger.exception("CalificacionCreateResponse validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La calificación se guardó pero hubo un error al armar la respuesta. Recargá el incidente.",
        ) from None


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
        select(Calificacion, Incidente, Usuario, AsignacionServicio, Pago)
        .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
        .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .where(Usuario.id == current_user.id)
    )
    total = int(
        db.scalar(
            select(func.count(Calificacion.id))
            .select_from(Calificacion)
            .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
            .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
            .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
            .where(Vehiculo.id_usuario == current_user.id),
        )
        or 0,
    )
    rows = db.execute(
        base.order_by(Calificacion.fecha.desc(), Calificacion.id.desc()).offset((page - 1) * page_size).limit(page_size),
    ).all()
    tecnico_ids = {asi.id_mecanico for _, _, _, asi, _ in rows if asi.id_mecanico is not None}
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    for _, _, _, asi, _ in rows:
        tid = asi.id_mecanico
        td = db.get(Taller, asi.id_taller)
        if td is not None and tid is not None:
            taller_map[tid] = td
    items = [
        _build_calificacion_item(
            cal=cal,
            inc=inc,
            asignacion=asi,
            cli=cli,
            pago=pago,
            tecnico_user=tech_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
            tecnico_taller=taller_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
        )
        for cal, inc, cli, asi, pago in rows
    ]
    return CalificacionListResponse(items=items, page=page, page_size=page_size, total=total)


def _build_admin_conditions(filters: CalificacionAdminFilters, *, mec: Usuario):
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
    if filters.tecnico and filters.tecnico.strip():
        term_t = _ilike_fragment_escaped(filters.tecnico[:120])
        conditions.append(
            or_(
                mec.nombre.ilike(term_t, escape="\\"),
                mec.apellido.ilike(term_t, escape="\\"),
            ),
        )
    if filters.taller and filters.taller.strip():
        term_w = _ilike_fragment_escaped(filters.taller[:120])
        conditions.append(Taller.nombre.ilike(term_w, escape="\\"))
    return conditions


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
    mec = aliased(Usuario)
    conditions = _build_admin_conditions(filters, mec=mec)

    count_stmt = (
        select(func.count(Calificacion.id))
        .select_from(Calificacion)
        .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
        .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .join(mec, mec.id == AsignacionServicio.id_mecanico)
        .join(Taller, Taller.id == AsignacionServicio.id_taller)
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
        .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
        .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .join(mec, mec.id == AsignacionServicio.id_mecanico)
        .join(Taller, Taller.id == AsignacionServicio.id_taller)
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
        select(Calificacion, Incidente, Usuario, AsignacionServicio, Pago)
        .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
        .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .join(mec, mec.id == AsignacionServicio.id_mecanico)
        .join(Taller, Taller.id == AsignacionServicio.id_taller)
    )
    if conditions:
        list_stmt = list_stmt.where(*conditions)
    rows = db.execute(
        list_stmt.order_by(Calificacion.fecha.desc(), Calificacion.id.desc()).offset((page - 1) * page_size).limit(page_size),
    ).all()

    tecnico_ids = {asi.id_mecanico for _, _, _, asi, _ in rows if asi.id_mecanico is not None}
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    for cal, inc, cli, asi, _pago in rows:
        tid = asi.id_mecanico
        td = db.get(Taller, asi.id_taller)
        if td is not None and tid is not None:
            taller_map[tid] = td
    items = [
        _build_calificacion_item(
            cal=cal,
            inc=inc,
            asignacion=asi,
            cli=cli,
            pago=pago,
            tecnico_user=tech_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
            tecnico_taller=taller_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
        )
        for cal, inc, cli, asi, pago in rows
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
    mec = aliased(Usuario)
    row = db.execute(
        select(Calificacion, Incidente, Usuario, AsignacionServicio, Pago)
        .join(AsignacionServicio, AsignacionServicio.id == Calificacion.id_asignacion)
        .join(Incidente, Incidente.id == AsignacionServicio.id_incidente)
        .join(Vehiculo, Vehiculo.id == Incidente.id_vehiculo)
        .join(Usuario, Usuario.id == Vehiculo.id_usuario)
        .outerjoin(Pago, Pago.incidente_id == Incidente.id)
        .join(mec, mec.id == AsignacionServicio.id_mecanico)
        .where(Calificacion.id == calificacion_id),
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calificación no encontrada.")
    cal, inc, cli, asi, pago = row
    tecnico_ids = {asi.id_mecanico} if asi.id_mecanico is not None else set()
    tech_map, taller_map = _get_tecnico_context(db, tecnico_ids)
    td = db.get(Taller, asi.id_taller)
    if td is not None and asi.id_mecanico is not None:
        taller_map[asi.id_mecanico] = td
    return _build_calificacion_item(
        cal=cal,
        inc=inc,
        asignacion=asi,
        cli=cli,
        pago=pago,
        tecnico_user=tech_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
        tecnico_taller=taller_map.get(asi.id_mecanico) if asi.id_mecanico is not None else None,
    )
