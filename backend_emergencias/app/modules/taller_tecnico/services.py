"""Lógica de negocio — gestión de talleres (CU06)."""

from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.taller_tecnico.models import Taller
from app.modules.taller_tecnico.schemas import TallerCreateRequest, TallerListItem, TallerListResponse, TallerUpdateRequest


def taller_to_item(t: Taller) -> TallerListItem:
    return TallerListItem(
        id=t.id,
        nombre=t.nombre,
        direccion=t.direccion,
        latitud=float(t.latitud) if t.latitud is not None else None,
        longitud=float(t.longitud) if t.longitud is not None else None,
        telefono=t.telefono,
        email=t.email,
        horario_atencion=t.horario_atencion,
        disponibilidad=bool(t.disponibilidad),
        capacidad_maxima=t.capacidad_max,
        calificacion=float(t.calificacion or 0),
        id_admin=t.id_admin,
    )


def _filtros_listado(q: str | None, activo: bool | None):
    parts = []
    if q and q.strip():
        like = f"%{q.strip()}%"
        parts.append(
            or_(
                Taller.nombre.ilike(like),
                Taller.direccion.ilike(like),
                Taller.email.ilike(like),
            ),
        )
    if activo is True:
        parts.append(Taller.disponibilidad.is_(True))
    elif activo is False:
        parts.append(Taller.disponibilidad.is_(False))
    if not parts:
        return True
    return and_(*parts)


def listar_talleres(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    activo: bool | None,
) -> TallerListResponse:
    cond = _filtros_listado(q, activo)
    count_base = select(func.count()).select_from(Taller)
    list_base = select(Taller)
    if cond is not True:
        count_base = count_base.where(cond)
        list_base = list_base.where(cond)
    total = db.scalar(count_base) or 0
    stmt = list_base.order_by(Taller.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.scalars(stmt).all()
    return TallerListResponse(
        items=[taller_to_item(t) for t in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def crear_taller(db: Session, admin_id: int, body: TallerCreateRequest) -> TallerListItem:
    email_str = str(body.email) if body.email is not None else None
    t = Taller(
        id_admin=admin_id,
        nombre=body.nombre.strip(),
        direccion=body.direccion.strip(),
        latitud=body.latitud,
        longitud=body.longitud,
        telefono=body.telefono.strip() if body.telefono else None,
        email=email_str,
        horario_atencion=body.horario_atencion.strip() if body.horario_atencion else None,
        capacidad_max=body.capacidad_maxima,
        disponibilidad=True,
        calificacion=Decimal("0.00"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return taller_to_item(t)


def obtener_taller(db: Session, taller_id: int) -> Taller | None:
    return db.get(Taller, taller_id)


def actualizar_taller(db: Session, t: Taller, body: TallerUpdateRequest) -> TallerListItem:
    data = body.model_dump(exclude_unset=True)
    if "nombre" in data and data["nombre"] is not None:
        t.nombre = str(data["nombre"]).strip()
    if "direccion" in data and data["direccion"] is not None:
        t.direccion = str(data["direccion"]).strip()
    if "latitud" in data:
        t.latitud = data["latitud"]
    if "longitud" in data:
        t.longitud = data["longitud"]
    if "telefono" in data:
        raw = data["telefono"]
        t.telefono = raw.strip() if raw else None
    if "email" in data:
        em = data["email"]
        t.email = str(em) if em is not None else None
    if "capacidad_maxima" in data and data["capacidad_maxima"] is not None:
        t.capacidad_max = int(data["capacidad_maxima"])
    if "horario_atencion" in data:
        raw = data["horario_atencion"]
        t.horario_atencion = raw.strip() if raw else None
    db.commit()
    db.refresh(t)
    return taller_to_item(t)


def desactivar_taller(db: Session, t: Taller) -> TallerListItem:
    t.disponibilidad = False
    db.commit()
    db.refresh(t)
    return taller_to_item(t)


def reactivar_taller(db: Session, t: Taller) -> TallerListItem:
    t.disponibilidad = True
    db.commit()
    db.refresh(t)
    return taller_to_item(t)
