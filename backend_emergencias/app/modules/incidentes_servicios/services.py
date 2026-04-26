"""Incidentes, evidencias y progreso del servicio (técnico asignado)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.incidentes_servicios.constants import (
    EVIDENCE_TYPES,
    ESTADO_INICIAL_INCIDENTE,
    ESTADO_PENDIENTE_IA,
    ESTADO_REVISION_MANUAL,
)
from app.modules.incidentes_servicios.models import Calificacion, Evidencia, Incidente, IncidenteTallerCandidato
from app.modules.incidentes_servicios.schemas import (
    EvidenceCreateResponse,
    CalificacionCreate,
    CalificacionResponse,
    IncidentAcceptRequest,
    IncidentCreateRequest,
    IncidentDetailResponse,
    IncidentFinalizeRequest,
    IncidenteClienteListItem,
    IncidenteVehiculoListItem,
    IncidentListItem,
    IncidentListResponse,
    IncidentRejectResponse,
    IncidentResponse,
    MAX_TEXTO_EVIDENCIA,
)
from app.modules.incidentes_servicios.ai_assignment_schemas import (
    AssignmentCandidatesResponse,
    AssignmentConfirmRequest,
    AssignmentOverrideRequest,
    IncidentIaProcessResponse,
    IncidentIaResultResponse,
)
from app.modules.incidentes_servicios.assignment_service import assignment_result_from_db
from app.modules.incidentes_servicios.incident_ai_pipeline import process_incident_ai_pipeline
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_ASIGNACION_CONFIRMADA,
    AUDIT_ACTION_ASIGNACION_OVERRIDE,
    AUDIT_ACTION_EVIDENCIA_ADD,
    AUDIT_ACTION_INCIDENTE_ACEPTADO,
    AUDIT_ACTION_INCIDENTE_AI_ENRICHED,
    AUDIT_ACTION_INCIDENTE_AI_FAILED,
    AUDIT_ACTION_INCIDENTE_CALIFICADO,
    AUDIT_ACTION_INCIDENTE_CANCELADO_CLIENTE,
    AUDIT_ACTION_INCIDENTE_ELIMINADO_CLIENTE,
    AUDIT_ACTION_INCIDENTE_CREATE,
    AUDIT_ACTION_INCIDENTE_EN_CAMINO,
    AUDIT_ACTION_INCIDENTE_EN_PROCESO,
    AUDIT_ACTION_INCIDENTE_FINALIZADO,
    AUDIT_ACTION_INCIDENTE_RECHAZADO,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
    AUDIT_MODULE_SISTEMA,
    registrar_bitacora,
)
from app.modules.sistema.idempotencia_service import (
    evidence_payload_fingerprint,
    find_evidence_idempotency,
    find_incident_idempotency,
    incident_payload_fingerprint,
    register_evidence_idempotency,
    register_incident_idempotency,
    validate_idempotency_key,
)
from app.modules.taller_tecnico.models import MecanicoTaller, Taller
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_AUDIO_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp4",
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
    },
)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 15 * 1024 * 1024

_IDEMPOTENCIA_SCHEMA_HINT = (
    "Falta la tabla idempotencia_registro. Ejecutá `alembic upgrade head` o el script "
    "`database/patch_idempotencia_registro.sql` contra la base, y reiniciá el API."
)


def _missing_idempotencia_table(exc: BaseException) -> bool:
    blob = f"{exc} {getattr(exc, 'orig', '') or ''}".lower()
    if "idempotencia_registro" not in blob:
        return False
    return (
        "does not exist" in blob
        or "no existe" in blob
        or "no such table" in blob
        or "undefinedtable" in blob.replace(" ", "")
    )


def _rol_nombre_normalizado(rol: object) -> str:
    nombre = getattr(rol, "nombre", None) or ""
    return str(nombre).strip().lower()


def _is_admin(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) in ("administrador", "admin") for r in user.roles)


def _is_cliente(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) == "cliente" for r in user.roles)


def _is_tecnico(user: Usuario) -> bool:
    return any(_rol_nombre_normalizado(r) == "tecnico" for r in user.roles)


def _assert_can_list_incidents(user: Usuario) -> None:
    if _is_admin(user) or _is_cliente(user) or _is_tecnico(user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Listado de incidentes no disponible para este rol.",
    )


def _upload_root() -> Path:
    return Path(settings.uploads_dir)


def _relative_storage_path(incidente_id: int, stored_name: str) -> str:
    return f"incidentes/{incidente_id}/{stored_name}"


def _extension_for_mime(mime: str) -> str:
    base = (mime or "").split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }
    return mapping.get(base, ".bin")


def _validate_file_magic(*, tipo: str, content_type: str | None, data: bytes) -> None:
    ct = (content_type or "").split(";")[0].strip().lower()
    if tipo == "foto":
        if ct not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tipo MIME no permitido para foto: {content_type}",
            )
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Imagen demasiado grande")
        if ct == "image/jpeg" and not (len(data) >= 3 and data[:3] == b"\xff\xd8\xff"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Archivo no parece JPEG válido")
        if ct == "image/png" and not (len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Archivo no parece PNG válido")
        if ct == "image/webp" and not (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Archivo no parece WEBP válido")
    elif tipo == "audio":
        if ct not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tipo MIME no permitido para audio: {content_type}",
            )
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio demasiado grande")


def _persist_upload(*, incidente_id: int, data: bytes, ext: str) -> str:
    root = _upload_root()
    dest_dir = root / "incidentes" / str(incidente_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = dest_dir / name
    path.write_bytes(data)
    return _relative_storage_path(incidente_id, name)


def _load_incident_for_access(
    db: Session,
    incidente_id: int,
    *,
    with_evidencias: bool,
) -> Incidente | None:
    opts = [selectinload(Incidente.vehiculo)]
    if with_evidencias:
        opts.append(selectinload(Incidente.evidencias))
    stmt = select(Incidente).options(*opts).where(Incidente.id == incidente_id)
    return db.execute(stmt).scalar_one_or_none()


def _tecnico_puede_ver_incidente(user: Usuario, inc: Incidente) -> bool:
    if inc.tecnico_id is not None and inc.tecnico_id == user.id:
        return True
    pendiente = _estado_incidente_normalizado(inc) == "pendiente"
    en_bolsa = pendiente and inc.tecnico_id is None
    return bool(en_bolsa)


def _assert_incident_access(db: Session, user: Usuario, incidente_id: int, *, with_evidencias: bool) -> Incidente:
    inc = _load_incident_for_access(db, incidente_id, with_evidencias=with_evidencias)
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    owner_id = inc.vehiculo.id_usuario
    if owner_id == user.id or _is_admin(user):
        return inc
    if _is_tecnico(user) and _tecnico_puede_ver_incidente(user, inc):
        return inc
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este incidente")


def _estado_incidente_normalizado(inc: Incidente) -> str:
    return (inc.estado or ESTADO_INICIAL_INCIDENTE).strip().lower()


def _estado_incidente_cancellation_key(inc: Incidente) -> str:
    """Clave única de estado para reglas de cancelación (soporta 'En Proceso', 'en_proceso', etc.)."""
    s = (inc.estado or ESTADO_INICIAL_INCIDENTE).strip().lower()
    return s.replace(" ", "_")


def _assert_client_owner_only(user: Usuario, incidente: Incidente) -> None:
    """Solo el cliente dueño puede mutar evidencias (no admin)."""
    if incidente.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    if incidente.vehiculo.id_usuario != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el cliente dueño puede adjuntar evidencias")
    if not _is_cliente(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden adjuntar evidencias")


def _incident_text_and_media_flags(inc: Incidente) -> tuple[str, bool, bool]:
    parts: list[str] = []
    if (inc.descripcion or "").strip():
        parts.append((inc.descripcion or "").strip())
    has_audio = False
    has_photo = False
    for ev in sorted(inc.evidencias or [], key=lambda x: x.id):
        tipo = (ev.tipo or "").strip().lower()
        if tipo == "texto" and (ev.contenido_texto or "").strip():
            parts.append((ev.contenido_texto or "").strip())
        elif tipo == "audio":
            has_audio = True
        elif tipo == "foto":
            has_photo = True
    return "\n".join(parts), has_audio, has_photo


def enrich_incident_with_ai(
    db: Session,
    incidente_id: int,
    *,
    id_usuario_actor: int,
    client_ip: str | None,
    force: bool = False,
) -> None:
    """Delega en el pipeline Gemini + asignación determinística (commits internos)."""
    process_incident_ai_pipeline(
        db,
        incidente_id,
        id_usuario_actor=id_usuario_actor,
        client_ip=client_ip,
        force=force,
    )


def _session_for_background_task() -> Session:
    """Usa la misma `sessionmaker` que los tests (`app.state.background_sessionmaker`) o `SessionLocal` prod."""
    from app.main import app

    factory = getattr(app.state, "background_sessionmaker", None)
    maker = factory if factory is not None else SessionLocal
    return maker()


def run_enrich_incident_with_ai_task(
    incidente_id: int,
    id_usuario_actor: int,
    client_ip: str | None,
    *,
    force: bool = False,
) -> None:
    db = _session_for_background_task()
    try:
        enrich_incident_with_ai(
            db,
            incidente_id,
            id_usuario_actor=id_usuario_actor,
            client_ip=client_ip,
            force=force,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Pipeline IA falló para incidente %s", incidente_id)
        try:
            registrar_bitacora(
                db,
                id_usuario=id_usuario_actor,
                modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
                accion=AUDIT_ACTION_INCIDENTE_AI_FAILED,
                ip=client_ip,
                resultado=(f"FAIL iid={incidente_id} err={exc!s}")[:50],
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("No se pudo registrar INCIDENTE_AI_FAILED en bitácora")
    finally:
        db.close()


def _to_incident_response(db: Session, inc: Incidente, *, evidencias_count: int | None = None) -> IncidentResponse:
    count = evidencias_count
    if count is None:
        count = int(db.scalar(select(func.count()).select_from(Evidencia).where(Evidencia.id_incidente == inc.id)) or 0)
    desc = (inc.descripcion or "").strip()
    cliente_id = inc.vehiculo.id_usuario if inc.vehiculo is not None else 0
    conf = inc.confianza_ia
    ai_result_dict = None
    if inc.ai_result_json:
        try:
            ai_result_dict = json.loads(inc.ai_result_json)
        except json.JSONDecodeError:
            ai_result_dict = None
    return IncidentResponse(
        id=inc.id,
        cliente_id=cliente_id,
        vehiculo_id=inc.id_vehiculo,
        estado=inc.estado or ESTADO_INICIAL_INCIDENTE,
        latitud=float(inc.latitud),
        longitud=float(inc.longitud),
        descripcion_texto=desc if desc else None,
        created_at=inc.fechacreacion,
        evidencias_count=count,
        categoria_ia=inc.categoria_ia,
        prioridad_ia=inc.prioridad_ia,
        resumen_ia=inc.resumen_ia,
        confianza_ia=float(conf) if conf is not None else None,
        tecnico_id=inc.tecnico_id,
        ai_status=inc.ai_status,
        ai_provider=inc.ai_provider,
        ai_model=inc.ai_model,
        prompt_version=inc.prompt_version,
        ai_result=ai_result_dict,
    )


def create_incident_for_client(
    db: Session,
    user: Usuario,
    payload: IncidentCreateRequest,
    *,
    client_ip: str | None,
    idempotency_key_raw: str | None,
) -> tuple[IncidentResponse, bool]:
    if not _is_cliente(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden reportar emergencias",
        )
    key = validate_idempotency_key(idempotency_key_raw)
    huella = incident_payload_fingerprint(payload)
    try:
        existing = find_incident_idempotency(db, id_usuario=user.id, idempotency_key=key)
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        if _missing_idempotencia_table(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_IDEMPOTENCIA_SCHEMA_HINT,
            ) from exc
        raise
    if existing is not None:
        if existing.huella_carga != huella:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key ya usada con otro cuerpo de solicitud.",
            )
        iid = existing.id_incidente_ref
        if iid is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registro de idempotencia inconsistente.",
            )
        inc = db.execute(
            select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == iid),
        ).scalar_one_or_none()
        if inc is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Incidente asociado a la clave ya no existe.",
            )
        return _to_incident_response(db, inc, evidencias_count=None), False

    v = db.get(Vehiculo, payload.vehiculo_id)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    if v.id_usuario != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El vehículo no pertenece al usuario autenticado",
        )
    desc = (payload.descripcion_texto or "").strip()
    inc = Incidente(
        id_vehiculo=v.id,
        latitud=Decimal(str(payload.latitud)),
        longitud=Decimal(str(payload.longitud)),
        descripcion=desc if desc else "",
        estado=ESTADO_PENDIENTE_IA,
    )
    db.add(inc)
    db.flush()
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_CREATE,
        ip=client_ip,
        resultado=f"OK iid={inc.id}"[:50],
    )
    try:
        register_incident_idempotency(
            db,
            id_usuario=user.id,
            idempotency_key=key,
            huella_carga=huella,
            id_incidente=inc.id,
        )
        db.commit()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        if _missing_idempotencia_table(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_IDEMPOTENCIA_SCHEMA_HINT,
            ) from exc
        raise
    db.refresh(inc)
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == inc.id),
    ).scalar_one()
    return _to_incident_response(db, inc, evidencias_count=0), True


def add_evidence_to_incident(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    tipo_raw: str,
    contenido_texto: str | None,
    file_bytes: bytes | None,
    file_content_type: str | None,
    client_ip: str | None,
) -> tuple[EvidenceCreateResponse, bool]:
    tipo = (tipo_raw or "").strip().lower()
    if tipo not in EVIDENCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tipo debe ser foto, audio o texto",
        )

    inc = _load_incident_for_access(db, incidente_id, with_evidencias=False)
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    _assert_client_owner_only(user, inc)

    url_rel = ""
    texto: str | None = None
    fp: str

    if tipo == "texto":
        t = (contenido_texto or "").strip()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="contenido_texto es obligatorio para tipo texto",
            )
        if len(t) > MAX_TEXTO_EVIDENCIA:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Texto demasiado largo")
        if file_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No enviar archivo para tipo texto",
            )
        texto = t
        url_rel = ""
        fp = evidence_payload_fingerprint(inc.id, tipo, file_bytes=None, contenido_texto=texto)
    else:
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="archivo es obligatorio para foto o audio",
            )
        _validate_file_magic(tipo=tipo, content_type=file_content_type, data=file_bytes)
        fp = evidence_payload_fingerprint(inc.id, tipo, file_bytes=file_bytes, contenido_texto=None)
        texto = None

    idempo = find_evidence_idempotency(db, id_usuario=user.id, fingerprint=fp)
    if idempo is not None and idempo.id_evidencia_ref is not None:
        ev0 = db.get(Evidencia, idempo.id_evidencia_ref)
        if ev0 is not None:
            return (
                EvidenceCreateResponse(
                    id=ev0.id,
                    incidente_id=ev0.id_incidente,
                    tipo=ev0.tipo,
                    url_or_path=ev0.urlarchivo or "",
                    created_at=ev0.fechasubida,
                ),
                False,
            )

    if tipo != "texto":
        ext = _extension_for_mime(file_content_type or "")
        url_rel = _persist_upload(incidente_id=inc.id, data=file_bytes or b"", ext=ext)

    ev = Evidencia(
        id_incidente=inc.id,
        tipo=tipo,
        urlarchivo=url_rel,
        contenido_texto=texto,
    )
    db.add(ev)
    db.flush()
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_EVIDENCIA_ADD,
        ip=client_ip,
        resultado=f"OK iid={inc.id} eid={ev.id}"[:50],
    )
    register_evidence_idempotency(
        db,
        id_usuario=user.id,
        fingerprint=fp,
        id_evidencia=ev.id,
        id_incidente=inc.id,
    )
    db.commit()
    db.refresh(ev)
    return (
        EvidenceCreateResponse(
            id=ev.id,
            incidente_id=ev.id_incidente,
            tipo=ev.tipo,
            url_or_path=ev.urlarchivo or "",
            created_at=ev.fechasubida,
        ),
        True,
    )


def _ilike_fragment_escaped(raw: str) -> str:
    """Patrón `%…%` para ILIKE con comodines escapados (PostgreSQL / SQLite)."""
    t = raw.strip()
    escaped = t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_incidents_paginated(
    db: Session,
    user: Usuario,
    *,
    page: int,
    page_size: int,
    estado: str | None,
    cliente: int | None,
    cliente_busqueda: str | None,
    vehiculo_placa: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
) -> IncidentListResponse:
    """Listado con filtros y paginación. Admin: todos + filtro por id cliente o texto en usuario."""
    _assert_can_list_incidents(user)

    conditions: list = []
    if _is_admin(user):
        if cliente is not None:
            conditions.append(Vehiculo.id_usuario == cliente)
        elif (qb := (cliente_busqueda or "").strip()):
            term = _ilike_fragment_escaped(qb[:100])
            conditions.append(
                or_(
                    Usuario.nombre.ilike(term, escape="\\"),
                    Usuario.apellido.ilike(term, escape="\\"),
                    Usuario.email.ilike(term, escape="\\"),
                ),
            )
    elif _is_cliente(user):
        conditions.append(Vehiculo.id_usuario == user.id)
    elif _is_tecnico(user):
        if cliente is not None or (cliente_busqueda or "").strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los filtros de cliente solo están disponibles para administradores.",
            )
        bolsa = and_(
            Incidente.estado == ESTADO_INICIAL_INCIDENTE,
            Incidente.tecnico_id.is_(None),
        )
        asignados_a_mi = Incidente.tecnico_id == user.id
        conditions.append(or_(bolsa, asignados_a_mi))

    if (pl := (vehiculo_placa or "").strip()):
        conditions.append(Vehiculo.placa.ilike(_ilike_fragment_escaped(pl[:32]), escape="\\"))

    if estado is not None and (s := estado.strip()):
        conditions.append(Incidente.estado == s)
    if fecha_desde is not None:
        conditions.append(Incidente.fechacreacion >= datetime.combine(fecha_desde, time.min))
    if fecha_hasta is not None:
        conditions.append(Incidente.fechacreacion <= datetime.combine(fecha_hasta, time.max))

    ev_sq = (
        select(Evidencia.id_incidente, func.count(Evidencia.id).label("evc"))
        .group_by(Evidencia.id_incidente)
        .subquery()
    )

    count_stmt = (
        select(func.count(Incidente.id))
        .select_from(Incidente)
        .join(Vehiculo, Incidente.id_vehiculo == Vehiculo.id)
        .join(Usuario, Vehiculo.id_usuario == Usuario.id)
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int(db.scalar(count_stmt) or 0)

    list_stmt = (
        select(Incidente, Vehiculo, Usuario, func.coalesce(ev_sq.c.evc, 0).label("evidencias_count"))
        .select_from(Incidente)
        .join(Vehiculo, Incidente.id_vehiculo == Vehiculo.id)
        .join(Usuario, Vehiculo.id_usuario == Usuario.id)
        .outerjoin(ev_sq, ev_sq.c.id_incidente == Incidente.id)
    )
    if conditions:
        list_stmt = list_stmt.where(*conditions)
    list_stmt = list_stmt.order_by(Incidente.fechacreacion.desc()).offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(list_stmt).all()
    items: list[IncidentListItem] = []
    for inc, veh, usr, evc in rows:
        nombre_completo = f"{(usr.nombre or '').strip()} {(usr.apellido or '').strip()}".strip() or usr.email
        marca_modelo = f"{(veh.marca or '').strip()} {(veh.modelo or '').strip()}".strip()
        items.append(
            IncidentListItem(
                id=inc.id,
                estado=inc.estado or ESTADO_INICIAL_INCIDENTE,
                created_at=inc.fechacreacion,
                cliente=IncidenteClienteListItem(id=usr.id, nombre=nombre_completo, email=usr.email),
                vehiculo=IncidenteVehiculoListItem(id=veh.id, placa=veh.placa, marca_modelo=marca_modelo),
                evidencias_count=int(evc),
                tecnico_id=inc.tecnico_id,
            ),
        )
    return IncidentListResponse(items=items, page=page, page_size=page_size, total=total)


def aceptar_solicitud(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
    body: IncidentAcceptRequest | None,
) -> IncidentDetailResponse:
    """Técnico: autoasignación; administrador: asignación explícita a un técnico."""
    if _is_cliente(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los clientes no pueden aceptar solicitudes.",
        )
    target_tecnico_id: int
    if _is_tecnico(user):
        if body is not None and body.tecnico_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El técnico autenticado no debe enviar tecnico_id en el cuerpo.",
            )
        target_tecnico_id = user.id
    elif _is_admin(user):
        if body is None or body.tecnico_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los administradores deben enviar tecnico_id en el cuerpo JSON.",
            )
        target_tecnico_id = body.tecnico_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos o administradores pueden aceptar solicitudes.",
        )

    tecnico_link = db.execute(
        select(MecanicoTaller)
        .join(Taller, Taller.id == MecanicoTaller.id_taller)
        .where(
            MecanicoTaller.id_usuario == target_tecnico_id,
            Taller.disponibilidad.is_(True),
        )
        .limit(1),
    ).scalar_one_or_none()
    if tecnico_link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El técnico debe estar asignado a un taller para aceptar solicitudes.",
        )

    stmt = (
        update(Incidente)
        .where(
            Incidente.id == incidente_id,
            Incidente.estado == ESTADO_INICIAL_INCIDENTE,
            Incidente.tecnico_id.is_(None),
        )
        .values(estado="Asignado", tecnico_id=target_tecnico_id)
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud ya no está disponible.",
        )
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_ACEPTADO,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} tid={target_tecnico_id}"[:50],
    )
    db.commit()
    return get_incident_detail(db, user, incidente_id)


def rechazar_solicitud(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
) -> IncidentRejectResponse:
    """Técnico: descarta una solicitud pendiente en bolsa; auditoría en bitácora, estado sin cambio."""
    if not _is_tecnico(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden rechazar solicitudes en bolsa.",
        )
    inc = _load_incident_for_access(db, incidente_id, with_evidencias=False)
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    if _estado_incidente_normalizado(inc) != "pendiente" or inc.tecnico_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede rechazar una solicitud pendiente disponible en bolsa.",
        )
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_RECHAZADO,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} tid={user.id}"[:50],
    )
    db.commit()
    return IncidentRejectResponse(ok=True, message="Rechazo registrado.")


_CU14_CANCELABLE_ESTADOS = frozenset(
    {"pendiente", "asignado", "pendiente_ia", "sugerido", "revision_manual"},
)
_CU14_ELIMINABLE_ESTADOS = frozenset({"cancelado", "finalizado", "pagado", "cerrado", "resuelto", "completado"})


def cancel_incident_by_client(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
) -> IncidentDetailResponse:
    """El cliente dueño cancela en estados iniciales permitidos (pendiente o asignado, sin desplazamiento aún)."""
    if not _is_cliente(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los clientes pueden cancelar sus propias solicitudes.",
        )
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    if inc.vehiculo is None or inc.vehiculo.id_usuario != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para cancelar este incidente.",
        )
    key = _estado_incidente_cancellation_key(inc)
    if key == "cancelado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud ya fue cancelada.",
        )
    if key not in _CU14_CANCELABLE_ESTADOS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar una solicitud en curso",
        )
    inc.estado = "Cancelado"
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_SISTEMA,
        accion=AUDIT_ACTION_INCIDENTE_CANCELADO_CLIENTE,
        ip=client_ip,
        resultado=f"OK iid={incidente_id}"[:50],
    )
    db.commit()
    return get_incident_detail(db, user, incidente_id)


def delete_incident_by_client(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
) -> None:
    """Borrado definitivo por cliente dueño para solicitudes cerradas/canceladas."""
    if not _is_cliente(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los clientes pueden eliminar sus solicitudes.",
        )
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    if inc.vehiculo is None or inc.vehiculo.id_usuario != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para eliminar este incidente.",
        )
    key = _estado_incidente_cancellation_key(inc)
    if key not in _CU14_ELIMINABLE_ESTADOS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden eliminar solicitudes canceladas o cerradas.",
        )
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_SISTEMA,
        accion=AUDIT_ACTION_INCIDENTE_ELIMINADO_CLIENTE,
        ip=client_ip,
        resultado=f"OK iid={incidente_id}"[:50],
    )
    del_res = db.execute(delete(Incidente).where(Incidente.id == incidente_id))
    if (del_res.rowcount or 0) < 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado.",
        )
    db.commit()


_ESTADO_EN_CAMINO = "En Camino"
_ESTADO_EN_PROCESO = "En Proceso"
_ESTADO_FINALIZADO = "Finalizado"


def _load_incident_for_mutation_progreso(db: Session, incidente_id: int) -> Incidente:
    inc = _load_incident_for_access(db, incidente_id, with_evidencias=False)
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    return inc


def _assert_solo_tecnico_asignado_puede_progreso(user: Usuario, inc: Incidente) -> None:
    if not _is_tecnico(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el técnico asignado puede actualizar el progreso de este servicio.",
        )
    if inc.tecnico_id is None or inc.tecnico_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el técnico asignado puede actualizar el progreso de este servicio.",
        )


def marcar_en_camino(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
) -> IncidentResponse:
    """Pasa de asignado a en camino."""
    inc = _load_incident_for_mutation_progreso(db, incidente_id)
    _assert_solo_tecnico_asignado_puede_progreso(user, inc)
    if _estado_incidente_cancellation_key(inc) != "asignado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede marcar 'En Camino' cuando el estado es Asignado.",
        )
    inc.estado = _ESTADO_EN_CAMINO
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_EN_CAMINO,
        ip=client_ip,
        resultado=f"OK iid={incidente_id}"[:50],
    )
    db.commit()
    db.refresh(inc)
    return _to_incident_response(db, inc)


def marcar_en_proceso(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    client_ip: str | None,
) -> IncidentResponse:
    """Pasa de en camino a en proceso."""
    inc = _load_incident_for_mutation_progreso(db, incidente_id)
    _assert_solo_tecnico_asignado_puede_progreso(user, inc)
    if _estado_incidente_cancellation_key(inc) != "en_camino":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede marcar 'En Proceso' cuando el estado es En Camino.",
        )
    inc.estado = _ESTADO_EN_PROCESO
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_EN_PROCESO,
        ip=client_ip,
        resultado=f"OK iid={incidente_id}"[:50],
    )
    db.commit()
    db.refresh(inc)
    return _to_incident_response(db, inc)


def finalizar_servicio(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    body: IncidentFinalizeRequest | None,
    client_ip: str | None,
) -> IncidentResponse:
    """Cierre: solo desde en proceso a finalizado. Diagnóstico y precio en bitácora si se envían (sin columnas en modelo)."""
    inc = _load_incident_for_mutation_progreso(db, incidente_id)
    _assert_solo_tecnico_asignado_puede_progreso(user, inc)
    if _estado_incidente_cancellation_key(inc) != "en_proceso":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede finalizar un incidente en estado En Proceso.",
        )
    inc.estado = _ESTADO_FINALIZADO
    resultado = f"OK iid={incidente_id}"[:50]
    if body is not None and body.precio_base is not None:
        resultado = f"OK iid={incidente_id} p={body.precio_base}"[:50]
    if body is not None and (body.diagnostico_final is not None and (body.diagnostico_final or "").strip()):
        tag = (body.diagnostico_final or "")[:20]
        extra = f" d={tag}"
        resultado = f"{resultado}{extra}"[:50]
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_FINALIZADO,
        ip=client_ip,
        resultado=resultado,
    )
    db.commit()
    db.refresh(inc)
    return _to_incident_response(db, inc)


def get_incident_detail(db: Session, user: Usuario, incidente_id: int) -> IncidentDetailResponse:
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=True)
    items = [
        EvidenceCreateResponse(
            id=e.id,
            incidente_id=e.id_incidente,
            tipo=e.tipo,
            url_or_path=e.urlarchivo or ("" if not e.contenido_texto else ""),
            created_at=e.fechasubida,
        )
        for e in sorted(inc.evidencias or [], key=lambda x: x.id)
    ]
    base = _to_incident_response(db, inc, evidencias_count=len(items))
    return IncidentDetailResponse(**base.model_dump(), evidencias=items)


_ESTADOS_PERMITIDOS_CALIFICAR = frozenset({"finalizado", "pagado"})


def crear_calificacion(
    db: Session,
    incidente_id: int,
    data: CalificacionCreate,
    current_user: Usuario,
    *,
    client_ip: str | None,
) -> CalificacionResponse:
    """Cliente dueño: una sola calificación por incidente, solo si el servicio está cerrado (finalizado o pagado)."""
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")

    if not _is_cliente(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los clientes pueden calificar un servicio.",
        )
    if inc.vehiculo.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para calificar este incidente.",
        )

    key = _estado_incidente_cancellation_key(inc)
    if key not in _ESTADOS_PERMITIDOS_CALIFICAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede calificar un incidente finalizado o pagado.",
        )

    existing = db.execute(select(Calificacion).where(Calificacion.id_incidente == incidente_id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este incidente ya tiene una calificación.",
        )

    row = Calificacion(
        id_incidente=incidente_id,
        puntuacion=data.puntuacion,
        comentario=data.comentario,
    )
    db.add(row)
    registrar_bitacora(
        db,
        id_usuario=current_user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_INCIDENTE_CALIFICADO,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} pts={data.puntuacion}"[:50],
    )
    db.commit()
    db.refresh(row)
    return CalificacionResponse(
        id=row.id,
        incidente_id=row.id_incidente,
        puntuacion=row.puntuacion,
        comentario=row.comentario,
        fecha=row.fecha,
    )


def _assert_admin(user: Usuario) -> None:
    if not _is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ejecutar esta acción.",
        )


def trigger_ia_process_endpoint(
    db: Session,
    user: Usuario,
    incidente_id: int,
    *,
    force: bool,
    client_ip: str | None,
) -> IncidentIaProcessResponse:
    if not (_is_admin(user) or _is_cliente(user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    if _is_cliente(user) and (inc.vehiculo is None or inc.vehiculo.id_usuario != user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")
    skipped, tag = process_incident_ai_pipeline(
        db,
        incidente_id,
        id_usuario_actor=user.id,
        client_ip=client_ip,
        force=force,
    )
    inc2 = db.get(Incidente, incidente_id)
    estado = inc2.estado if inc2 else (inc.estado or "")
    return IncidentIaProcessResponse(
        incidente_id=incidente_id,
        ai_status=(inc2.ai_status if inc2 else None) or "",
        estado=estado,
        skipped=skipped,
    )


def get_incident_ia_result_endpoint(db: Session, user: Usuario, incidente_id: int) -> IncidentIaResultResponse:
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    parsed = None
    if inc.ai_result_json and (inc.ai_status or "").lower() not in ("failed", "processing"):
        try:
            from app.modules.incidentes_servicios.ai_assignment_schemas import AiIncidentResult

            parsed = AiIncidentResult.model_validate_json(inc.ai_result_json)
        except Exception:
            parsed = None
    return IncidentIaResultResponse(
        incidente_id=incidente_id,
        ai_status=inc.ai_status,
        estado=inc.estado or ESTADO_INICIAL_INCIDENTE,
        ai_provider=inc.ai_provider,
        ai_model=inc.ai_model,
        prompt_version=inc.prompt_version,
        result=parsed,
    )


def list_assignment_candidates_endpoint(db: Session, user: Usuario, incidente_id: int) -> AssignmentCandidatesResponse:
    inc = _assert_incident_access(db, user, incidente_id, with_evidencias=False)
    ar = assignment_result_from_db(db, incidente_id)
    trace = None
    if inc.assignment_trace_json:
        try:
            trace = json.loads(inc.assignment_trace_json)
        except json.JSONDecodeError:
            trace = None
    return AssignmentCandidatesResponse(
        incidente_id=incidente_id,
        estado=inc.estado or ESTADO_INICIAL_INCIDENTE,
        candidates=ar.candidates if ar else [],
        assignment_trace=trace,
    )


def confirm_assignment_endpoint(
    db: Session,
    user: Usuario,
    incidente_id: int,
    body: AssignmentConfirmRequest,
    *,
    client_ip: str | None,
) -> IncidentDetailResponse:
    _assert_admin(user)
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")
    if _estado_incidente_normalizado(inc) != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede confirmar con incidente en bolsa (Pendiente).",
        )
    if (inc.ai_status or "").strip().lower() != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La IA aún no completó o requiere revisión manual.",
        )
    row = db.execute(
        select(IncidenteTallerCandidato).where(
            IncidenteTallerCandidato.id_incidente == incidente_id,
            IncidenteTallerCandidato.id_taller == body.taller_id,
        ),
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no está en la lista de candidatos.")
    tid = row.id_tecnico_sugerido
    if tid is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay técnico sugerido para ese taller.",
        )
    inc.estado = "Asignado"
    inc.tecnico_id = int(tid)
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_ASIGNACION_CONFIRMADA,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} tid={tid}"[:50],
    )
    db.commit()
    return get_incident_detail(db, user, incidente_id)


def override_assignment_endpoint(
    db: Session,
    user: Usuario,
    incidente_id: int,
    body: AssignmentOverrideRequest,
    *,
    client_ip: str | None,
) -> IncidentDetailResponse:
    _assert_admin(user)
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == incidente_id),
    ).scalar_one_or_none()
    if inc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado.")
    st = _estado_incidente_normalizado(inc)
    if st not in ("pendiente", "revision_manual"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Override permitido solo en Pendiente o Revision manual.",
        )
    link = db.execute(
        select(MecanicoTaller).where(
            MecanicoTaller.id_taller == body.taller_id,
            MecanicoTaller.id_usuario == body.tecnico_id,
        ),
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El técnico no pertenece al taller indicado.",
        )
    inc.estado = "Asignado"
    inc.tecnico_id = body.tecnico_id
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_INCIDENTES_SERVICIOS,
        accion=AUDIT_ACTION_ASIGNACION_OVERRIDE,
        ip=client_ip,
        resultado=f"OK iid={incidente_id} tid={body.tecnico_id}"[:50],
    )
    db.commit()
    return get_incident_detail(db, user, incidente_id)
