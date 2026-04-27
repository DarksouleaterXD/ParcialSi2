from datetime import datetime

from pydantic import BaseModel


class ModuloSistemaHealth(BaseModel):
    modulo: str
    status: str


class BitacoraUsuarioRef(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str


class BitacoraListItem(BaseModel):
    id: int
    id_usuario: int
    modulo: str
    accion: str
    ip_origen: str | None
    resultado: str | None
    fecha_hora: datetime | None
    usuario: BitacoraUsuarioRef


class BitacoraListResponse(BaseModel):
    items: list[BitacoraListItem]
    total: int
    page: int
    page_size: int


class BitacoraDetailResponse(BaseModel):
    id: int
    id_usuario: int
    modulo: str
    accion: str
    ip_origen: str | None
    resultado: str | None
    fecha_hora: datetime | None
    usuario: BitacoraUsuarioRef


# --- Notificaciones (CU-17) ---


class NotificacionItem(BaseModel):
    id: int
    titulo: str
    mensaje: str
    leida: bool
    tipo: str | None = None
    fecha_hora: datetime | None = None


class NotificacionListResponse(BaseModel):
    items: list[NotificacionItem]
    total: int
    page: int
    page_size: int


class NoLeidasCount(BaseModel):
    count: int


class NotificacionPatch(BaseModel):
    leida: bool = True


class MarcarTodasLeidasResponse(BaseModel):
    updated: int


class PushTokenIn(BaseModel):
    token: str
    plataforma: str = "android"


class PushTokenUnregisterIn(BaseModel):
    token: str
