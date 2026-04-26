"""Registro de idempotencia para POST de incidentes y evidencias (reintentos móviles)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.sistema.models import IdempotenciaRegistro

if TYPE_CHECKING:
    from app.modules.incidentes_servicios.schemas import IncidentCreateRequest

SCOPE_INCIDENTE_CREAR = "incidente_crear"
SCOPE_EVIDENCIA_SUBIR = "evidencia_subir"

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

TTL_HOURS = 48


def purge_expired_idempotency_rows(db: Session) -> None:
    now = datetime.utcnow()
    db.execute(delete(IdempotenciaRegistro).where(IdempotenciaRegistro.expira_en < now))


def validate_idempotency_key(raw: str | None) -> str:
    if raw is None or not (key := raw.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Header Idempotency-Key obligatorio (8-128 caracteres alfanuméricos, puntos, guiones).",
        )
    if not _IDEMPOTENCY_KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key inválido: usar 8-128 caracteres [A-Za-z0-9._-].",
        )
    return key


def incident_payload_fingerprint(payload: IncidentCreateRequest) -> str:
    desc = (payload.descripcion_texto or "").strip() or None
    body = {
        "descripcion_texto": desc,
        "latitud": round(float(payload.latitud), 6),
        "longitud": round(float(payload.longitud), 6),
        "vehiculo_id": int(payload.vehiculo_id),
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evidence_payload_fingerprint(
    incidente_id: int,
    tipo: str,
    *,
    file_bytes: bytes | None,
    contenido_texto: str | None,
) -> str:
    fh = hashlib.sha256(file_bytes or b"").hexdigest()
    tx = (contenido_texto or "").strip()
    raw = f"{int(incidente_id)}\n{tipo}\n{fh}\n{tx}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=TTL_HOURS)


def find_incident_idempotency(
    db: Session,
    *,
    id_usuario: int,
    idempotency_key: str,
) -> IdempotenciaRegistro | None:
    purge_expired_idempotency_rows(db)
    return db.execute(
        select(IdempotenciaRegistro).where(
            IdempotenciaRegistro.id_usuario == id_usuario,
            IdempotenciaRegistro.alcance == SCOPE_INCIDENTE_CREAR,
            IdempotenciaRegistro.clave == idempotency_key,
        ),
    ).scalar_one_or_none()


def register_incident_idempotency(
    db: Session,
    *,
    id_usuario: int,
    idempotency_key: str,
    huella_carga: str,
    id_incidente: int,
) -> None:
    row = IdempotenciaRegistro(
        alcance=SCOPE_INCIDENTE_CREAR,
        clave=idempotency_key,
        id_usuario=id_usuario,
        huella_carga=huella_carga,
        id_incidente_ref=id_incidente,
        id_evidencia_ref=None,
        expira_en=_expiry(),
    )
    db.add(row)


def find_evidence_idempotency(db: Session, *, id_usuario: int, fingerprint: str) -> IdempotenciaRegistro | None:
    purge_expired_idempotency_rows(db)
    return db.execute(
        select(IdempotenciaRegistro).where(
            IdempotenciaRegistro.id_usuario == id_usuario,
            IdempotenciaRegistro.alcance == SCOPE_EVIDENCIA_SUBIR,
            IdempotenciaRegistro.clave == fingerprint,
        ),
    ).scalar_one_or_none()


def register_evidence_idempotency(
    db: Session,
    *,
    id_usuario: int,
    fingerprint: str,
    id_evidencia: int,
    id_incidente: int,
) -> None:
    row = IdempotenciaRegistro(
        alcance=SCOPE_EVIDENCIA_SUBIR,
        clave=fingerprint,
        id_usuario=id_usuario,
        huella_carga=fingerprint,
        id_incidente_ref=id_incidente,
        id_evidencia_ref=id_evidencia,
        expira_en=_expiry(),
    )
    db.add(row)
