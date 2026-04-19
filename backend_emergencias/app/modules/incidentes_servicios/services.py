"""CU-09: creación de incidentes y evidencias (sin IA ni asignación)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.incidentes_servicios.constants import (
    EVIDENCE_TYPES,
    ESTADO_INICIAL_INCIDENTE,
    TERMINAL_ESTADOS_INCIDENTE,
)
from app.modules.incidentes_servicios.models import Evidencia, Incidente
from app.modules.incidentes_servicios.schemas import (
    EvidenceCreateResponse,
    IncidentCreateRequest,
    IncidentDetailResponse,
    IncidentResponse,
    MAX_TEXTO_EVIDENCIA,
)
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_EVIDENCIA_ADD,
    AUDIT_ACTION_INCIDENTE_CREATE,
    AUDIT_MODULE_INCIDENTES_SERVICIOS,
    registrar_bitacora,
)
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo

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


def _is_admin(user: Usuario) -> bool:
    return any(r.nombre == "Administrador" for r in user.roles)


def _is_cliente(user: Usuario) -> bool:
    return any(r.nombre == "Cliente" for r in user.roles)


def _vehiculo_tiene_incidente_activo(db: Session, vehiculo_id: int) -> bool:
    estados = db.scalars(select(Incidente.estado).where(Incidente.id_vehiculo == vehiculo_id)).all()
    for est in estados:
        if (est or "").strip().lower() not in TERMINAL_ESTADOS_INCIDENTE:
            return True
    return False


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


def _assert_incident_access(db: Session, user: Usuario, incidente_id: int, *, with_evidencias: bool) -> Incidente:
    inc = _load_incident_for_access(db, incidente_id, with_evidencias=with_evidencias)
    if inc is None or inc.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    owner_id = inc.vehiculo.id_usuario
    if owner_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este incidente")
    return inc


def _assert_client_owner_only(user: Usuario, incidente: Incidente) -> None:
    """Solo el cliente dueño puede mutar evidencias (no admin)."""
    if incidente.vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    if incidente.vehiculo.id_usuario != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el cliente dueño puede adjuntar evidencias")
    if not _is_cliente(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo clientes pueden adjuntar evidencias")


def _to_incident_response(db: Session, inc: Incidente, *, evidencias_count: int | None = None) -> IncidentResponse:
    count = evidencias_count
    if count is None:
        count = int(db.scalar(select(func.count()).select_from(Evidencia).where(Evidencia.id_incidente == inc.id)) or 0)
    desc = (inc.descripcion or "").strip()
    cliente_id = inc.vehiculo.id_usuario if inc.vehiculo is not None else 0
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
    )


def create_incident_for_client(
    db: Session,
    user: Usuario,
    payload: IncidentCreateRequest,
    *,
    client_ip: str | None,
) -> IncidentResponse:
    if not _is_cliente(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden reportar emergencias",
        )
    v = db.get(Vehiculo, payload.vehiculo_id)
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    if v.id_usuario != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El vehículo no pertenece al usuario autenticado",
        )
    if _vehiculo_tiene_incidente_activo(db, v.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El vehículo ya tiene un incidente activo",
        )

    desc = (payload.descripcion_texto or "").strip()
    inc = Incidente(
        id_vehiculo=v.id,
        latitud=Decimal(str(payload.latitud)),
        longitud=Decimal(str(payload.longitud)),
        descripcion=desc if desc else "",
        estado=ESTADO_INICIAL_INCIDENTE,
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
    db.commit()
    db.refresh(inc)
    inc = db.execute(
        select(Incidente).options(selectinload(Incidente.vehiculo)).where(Incidente.id == inc.id),
    ).scalar_one()
    return _to_incident_response(db, inc, evidencias_count=0)


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
) -> EvidenceCreateResponse:
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
    else:
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="archivo es obligatorio para foto o audio",
            )
        _validate_file_magic(tipo=tipo, content_type=file_content_type, data=file_bytes)
        ext = _extension_for_mime(file_content_type or "")
        url_rel = _persist_upload(incidente_id=inc.id, data=file_bytes, ext=ext)
        texto = None

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
    db.commit()
    db.refresh(ev)
    return EvidenceCreateResponse(
        id=ev.id,
        incidente_id=ev.id_incidente,
        tipo=ev.tipo,
        url_or_path=ev.urlarchivo or "",
        created_at=ev.fechasubida,
    )


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
