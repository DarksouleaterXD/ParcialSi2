"""Registro de auditoría (bitácora). Consumido por otros módulos vía `record_audit_event`."""

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.modules.sistema.models import Bitacora

# Dominio: acciones de autenticación bajo el paquete `usuario_autenticacion`
AUDIT_MODULE_USER_AUTH = "usuario_autenticacion"
AUDIT_ACTION_LOGIN = "LOGIN"
AUDIT_ACTION_LOGOUT = "LOGOUT"
AUDIT_ACTION_USUARIO_CREAR = "USUARIO_CREAR"
AUDIT_ACTION_USUARIO_EDITAR = "USUARIO_EDITAR"
AUDIT_ACTION_USUARIO_DESACTIVAR = "USUARIO_DESACTIVAR"
AUDIT_ACTION_ROLE_CREATE = "ROLE_CREATE"
AUDIT_ACTION_ROLE_UPDATE = "ROLE_UPDATE"
AUDIT_ACTION_ROLE_DELETE = "ROLE_DELETE"
AUDIT_ACTION_ROLE_ASSIGN = "ROLE_ASSIGN"
AUDIT_ACTION_ROLE_UNASSIGN = "ROLE_UNASSIGN"
AUDIT_MODULE_TALLER_TECHNICO = "taller_tecnico"
AUDIT_ACTION_TECHNICIAN_CREATE = "TECHNICIAN_CREATE"
AUDIT_ACTION_TECHNICIAN_UPDATE = "TECHNICIAN_UPDATE"
AUDIT_ACTION_TECHNICIAN_DEACTIVATE = "TECHNICIAN_DEACTIVATE"
AUDIT_MODULE_INCIDENTES_SERVICIOS = "incidentes_servicios"
AUDIT_ACTION_INCIDENTE_CREATE = "INCIDENTE_CREATE"
AUDIT_ACTION_EVIDENCIA_ADD = "EVIDENCIA_ADD"


class BitacoraEventCreate(BaseModel):
    """Contrato para un evento de auditoría persistido en `Bitacora` (sin secretos)."""

    user_id: int = Field(..., ge=1)
    module: str = Field(..., max_length=50)
    action: str = Field(..., max_length=100)
    client_ip: str | None = Field(default=None, max_length=45)
    outcome: str | None = Field(default=None, max_length=50)

    @field_validator("module", "action", "outcome", mode="before")
    @classmethod
    def strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


def record_audit_event(db: Session, event: BitacoraEventCreate) -> None:
    row = Bitacora(
        id_usuario=event.user_id,
        modulo=event.module,
        accion=event.action,
        iporigen=event.client_ip,
        resultado=event.outcome,
    )
    db.add(row)


def registrar_bitacora(
    db: Session,
    *,
    id_usuario: int,
    modulo: str,
    accion: str,
    ip: str | None,
    resultado: str | None,
) -> None:
    """Compatibilidad con llamadas existentes; delega en `BitacoraEventCreate`."""
    record_audit_event(
        db,
        BitacoraEventCreate(
            user_id=id_usuario,
            module=modulo,
            action=accion,
            client_ip=ip,
            outcome=resultado,
        ),
    )
