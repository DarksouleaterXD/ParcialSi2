from datetime import datetime

from pydantic import BaseModel, Field, field_validator

MAX_DESCRIPCION_INCIDENTE = 1000
MAX_TEXTO_EVIDENCIA = 10_000


class IncidentesHealth(BaseModel):
    modulo: str
    status: str


class IncidentCreateRequest(BaseModel):
    """Cuerpo JSON para `POST /incidentes`.

    Ejemplo:
    ```json
    {"vehiculo_id": 3, "latitud": -34.6037, "longitud": -58.3816, "descripcion_texto": "Pinchazo en ruta"}
    ```
    """

    vehiculo_id: int = Field(..., ge=1, description="Vehículo del cliente (debe ser propio)")
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)
    descripcion_texto: str | None = Field(None, max_length=MAX_DESCRIPCION_INCIDENTE)

    @field_validator("descripcion_texto", mode="before")
    @classmethod
    def strip_optional_description(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class IncidentResponse(BaseModel):
    """Respuesta estándar de incidente (listado / creación resumida).

    Ejemplo:
    ```json
    {
      "id": 1,
      "cliente_id": 2,
      "vehiculo_id": 3,
      "estado": "Pendiente",
      "latitud": -34.6037,
      "longitud": -58.3816,
      "descripcion_texto": "Pinchazo",
      "created_at": "2026-04-17T12:00:00",
      "evidencias_count": 0
    }
    ```
    """

    id: int
    cliente_id: int
    vehiculo_id: int
    estado: str
    latitud: float
    longitud: float
    descripcion_texto: str | None
    created_at: datetime | None
    evidencias_count: int


class EvidenceCreateResponse(BaseModel):
    """Evidencia creada o ítem en detalle de incidente.

    `url_or_path` es ruta relativa bajo el directorio de uploads (p. ej. `incidentes/12/uuid.jpg`), o vacío si es solo texto.
    """

    id: int
    incidente_id: int
    tipo: str
    url_or_path: str
    created_at: datetime | None


class IncidentDetailResponse(IncidentResponse):
    """Detalle para confirmación en app; incluye lista de evidencias."""

    evidencias: list[EvidenceCreateResponse] = Field(default_factory=list)
