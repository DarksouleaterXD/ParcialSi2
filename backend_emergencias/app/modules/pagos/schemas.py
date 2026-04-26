from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PagosHealth(BaseModel):
    modulo: str
    status: str


class PagoCreateRequest(BaseModel):
    monto_total: float = Field(..., gt=0, description="Monto total del servicio")
    metodo_pago: str = Field(default="TARJETA_SIMULADA", min_length=1, max_length=50)

    @field_validator("metodo_pago", mode="before")
    @classmethod
    def normalize_metodo_pago(cls, v: object) -> object:
        if isinstance(v, str):
            s = v.strip().upper()
            return s if s else "TARJETA_SIMULADA"
        return v


class PagoResponse(BaseModel):
    id: int
    incidente_id: int
    cliente_id: int
    tecnico_id: int
    monto_total: float
    monto_taller: float
    comision_plataforma: float
    metodo_pago: str
    estado: str
    created_at: datetime | None


class PagoListResponse(BaseModel):
    items: list[PagoResponse]
    total: int
    page: int
    page_size: int
