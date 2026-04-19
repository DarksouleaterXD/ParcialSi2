from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, PlainValidator, field_validator


def _email_flexible(v: object) -> str:
    if not isinstance(v, str):
        raise TypeError("email inválido")
    s = v.strip().lower()
    if "@" not in s:
        raise ValueError("email inválido")
    local, domain = s.rsplit("@", 1)
    if not local or not domain:
        raise ValueError("email inválido")
    return s


EmailFlexible = Annotated[str, PlainValidator(_email_flexible)]


class LoginRequest(BaseModel):
    email: EmailFlexible
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    roles: list[str]
    redirect_hint: str


class MeResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    estado: str | None
    roles: list[str]
    foto_perfil: str | None = None
    fecha_registro: datetime | None = None


class ProfileSelfUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    telefono: str | None = Field(None, max_length=20)
    foto_perfil: str | None = Field(None, max_length=255)


class PasswordChangeRequest(BaseModel):
    password_actual: str = Field(min_length=1)
    password_nueva: str = Field(min_length=1)
    password_confirmacion: str = Field(min_length=1)


class UsuarioListItem(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    estado: str | None
    roles: list[str]

    model_config = {"from_attributes": True}


class UsuarioListResponse(BaseModel):
    items: list[UsuarioListItem]
    total: int
    page: int
    page_size: int


class UsuarioCreateRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: EmailFlexible
    telefono: str | None = Field(None, max_length=20)
    id_rol: int = Field(description="ID del rol en tabla rol (Administrador, Cliente, Tecnico)")
    # Si se envían ambas y coinciden, se usa esta contraseña; si no, se genera una automática.
    password: str | None = Field(None, max_length=128)
    password_confirmacion: str | None = Field(None, max_length=128)


class UsuarioCreateResponse(BaseModel):
    id: int
    email: str
    password_generada: str
    roles: list[str]


class RolItem(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    permisos: list[str] = []


class PermisoCatalogoItem(BaseModel):
    codigo: str
    descripcion: str


class RolCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    descripcion: str | None = Field(None, max_length=255)
    permisos: list[str] = Field(default_factory=list)


class RolUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=50)
    descripcion: str | None = Field(None, max_length=255)
    permisos: list[str] | None = None


class UsuarioUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    email: EmailFlexible | None = None
    telefono: str | None = Field(None, max_length=20)
    estado: str | None = Field(None, max_length=50)
    id_rol: int | None = None
    password_nueva: str | None = Field(None, max_length=128)
    password_confirmacion: str | None = Field(None, max_length=128)


class UsuarioRolAssignRequest(BaseModel):
    id_rol: int = Field(..., ge=1)


# --- Vehículos ---


class VehiculoItem(BaseModel):
    id: int
    id_usuario: int
    placa: str
    marca: str
    modelo: str
    anio: int
    color: str | None
    tipo_seguro: str | None
    foto_frontal: str | None
    propietario_nombre: str | None = None
    propietario_email: str | None = None


class VehiculoListResponse(BaseModel):
    items: list[VehiculoItem]
    total: int
    page: int
    page_size: int


class VehiculoCreateRequest(BaseModel):
    placa: str = Field(..., min_length=1, max_length=20)
    marca: str = Field(..., min_length=1, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=50)
    anio: int = Field(..., ge=1980, le=2035)
    color: str | None = Field(None, max_length=30)
    tipo_seguro: str | None = Field(None, max_length=50)
    foto_frontal: str | None = Field(None, max_length=255)
    id_usuario: int | None = Field(None, description="Solo administrador: crear vehículo para otro usuario")

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        return v.strip().upper()


class VehiculoUpdateRequest(BaseModel):
    placa: str | None = Field(None, min_length=1, max_length=20)
    marca: str | None = Field(None, min_length=1, max_length=50)
    modelo: str | None = Field(None, min_length=1, max_length=50)
    anio: int | None = Field(None, ge=1980, le=2035)
    color: str | None = Field(None, max_length=30)
    tipo_seguro: str | None = Field(None, max_length=50)
    foto_frontal: str | None = Field(None, max_length=255)
    id_usuario: int | None = Field(None, description="Solo administrador: reasignar propietario")

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip().upper()
