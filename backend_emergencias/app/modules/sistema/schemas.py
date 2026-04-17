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
