from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class CalificacionCreateRequest(BaseModel):
    puntuacion: int = Field(..., ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=500)

    @field_validator("comentario", mode="before")
    @classmethod
    def _strip_comentario(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class ClienteRef(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str | None = None


class TallerRef(BaseModel):
    id: int
    nombre: str


class TecnicoRef(BaseModel):
    id: int
    nombre: str
    apellido: str


class ServicioRef(BaseModel):
    id: int
    estado: str


class IncidenteRef(BaseModel):
    id: int
    estado: str
    tipo: str | None = None


class PagoRef(BaseModel):
    id: int
    monto_total: float
    estado: str


class CalificacionItemResponse(BaseModel):
    id: int
    servicio_id: int
    incidente_id: int
    puntuacion: int
    comentario: str | None
    fecha: datetime | None
    cliente: ClienteRef
    taller: TallerRef | None = None
    tecnico: TecnicoRef | None = None
    servicio: ServicioRef | None = None
    incidente: IncidenteRef | None = None
    pago: PagoRef | None = None


class CalificacionListSummary(BaseModel):
    promedio_puntuacion: float
    cantidad_1: int
    cantidad_2: int
    cantidad_3: int
    cantidad_4: int
    cantidad_5: int


class CalificacionListResponse(BaseModel):
    items: list[CalificacionItemResponse]
    page: int
    page_size: int
    total: int
    summary: CalificacionListSummary | None = None


class CalificacionAdminFilters(BaseModel):
    cliente: str | None = None
    taller: str | None = None
    tecnico: str | None = None
    puntuacion: int | None = Field(default=None, ge=1, le=5)
    puntuacion_min: int | None = Field(default=None, ge=1, le=5)
    puntuacion_max: int | None = Field(default=None, ge=1, le=5)
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    estado_servicio: str | None = None
