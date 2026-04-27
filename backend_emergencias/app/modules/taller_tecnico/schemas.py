from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator

TechnicianSpecialty = Literal["battery", "tires", "engine", "general"]


class TallerTecnicoHealth(BaseModel):
    modulo: str
    status: str


class TallerCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    direccion: str = Field(..., min_length=1, max_length=255)
    latitud: Decimal = Field(..., description="Latitud WGS84 (-90..90)")
    longitud: Decimal = Field(..., description="Longitud WGS84 (-180..180)")
    telefono: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    capacidad_maxima: int = Field(..., ge=1, le=50000, description="Capacidad máxima de atención")
    horario_atencion: str | None = Field(None, max_length=120)

    @field_validator("latitud")
    @classmethod
    def validar_latitud(cls, v: Decimal) -> Decimal:
        x = float(v)
        if x < -90 or x > 90:
            raise ValueError("Latitud fuera de rango (-90 a 90).")
        return v

    @field_validator("longitud")
    @classmethod
    def validar_longitud(cls, v: Decimal) -> Decimal:
        x = float(v)
        if x < -180 or x > 180:
            raise ValueError("Longitud fuera de rango (-180 a 180).")
        return v


class TallerUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    direccion: str | None = Field(None, min_length=1, max_length=255)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    telefono: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    capacidad_maxima: int | None = Field(None, ge=1, le=50000)
    horario_atencion: str | None = Field(None, max_length=120)

    @model_validator(mode="after")
    def gps_par(self) -> "TallerUpdateRequest":
        has_lat = self.latitud is not None
        has_lon = self.longitud is not None
        if has_lat != has_lon:
            raise ValueError("Indicá latitud y longitud juntas, o ninguna.")
        return self

    @field_validator("latitud")
    @classmethod
    def validar_latitud(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        x = float(v)
        if x < -90 or x > 90:
            raise ValueError("Latitud fuera de rango (-90 a 90).")
        return v

    @field_validator("longitud")
    @classmethod
    def validar_longitud(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        x = float(v)
        if x < -180 or x > 180:
            raise ValueError("Longitud fuera de rango (-180 a 180).")
        return v


class TallerListItem(BaseModel):
    id: int
    nombre: str
    direccion: str
    latitud: float | None
    longitud: float | None
    telefono: str | None
    email: str | None
    horario_atencion: str | None
    disponibilidad: bool
    capacidad_maxima: int
    calificacion: float
    id_admin: int


class TallerListResponse(BaseModel):
    items: list[TallerListItem]
    total: int
    page: int
    page_size: int


class TechnicianCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: str | None = Field(None, max_length=20)
    especialidad: TechnicianSpecialty
    password: str | None = Field(None, max_length=128)
    password_confirmacion: str | None = Field(None, max_length=128)


class TechnicianUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(None, max_length=20)
    especialidad: TechnicianSpecialty | None = None


class TechnicianListItem(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    especialidad: str | None
    taller_id: int
    estado: str | None


class TechnicianListResponse(BaseModel):
    items: list[TechnicianListItem]
    total: int
    page: int
    page_size: int


class TechnicianCreateResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    especialidad: str | None
    taller_id: int
    estado: str | None
    password_generada: str
