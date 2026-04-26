from datetime import datetime
from typing import Any

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

    Ejemplo (tras tarea de fondo de enriquecimiento IA simulado):
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
      "evidencias_count": 0,
      "categoria_ia": "Neumáticos",
      "prioridad_ia": "MEDIA",
      "resumen_ia": "Pinchazo reportado.",
      "confianza_ia": 0.87
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
    categoria_ia: str | None = Field(default=None, description="Clasificación simulada (stub local)")
    prioridad_ia: str | None = Field(default=None, description="Prioridad simulada (stub local)")
    resumen_ia: str | None = Field(default=None, description="Resumen simulado (stub local)")
    confianza_ia: float | None = Field(default=None, description="Confianza heurística 0–1 (stub local)")
    tecnico_id: int | None = Field(default=None, description="Usuario técnico asignado al incidente")
    ai_status: str | None = Field(default=None, description="Estado del pipeline IA (pending, completed, …)")
    ai_provider: str | None = Field(default=None, description="Proveedor usado (google_gemini o local_fallback)")
    ai_model: str | None = Field(default=None, description="Modelo o heurística usada")
    prompt_version: str | None = Field(default=None, description="Versión del prompt contratado")
    ai_result: dict[str, Any] | None = Field(default=None, description="Resultado IA estructurado (JSON)")


class IncidentAcceptRequest(BaseModel):
    """Solo **Administrador**: indica a qué técnico asignar. El técnico autenticado no envía cuerpo."""

    tecnico_id: int | None = Field(default=None, ge=1, description="ID usuario con rol técnico a asignar")


class IncidentFinalizeRequest(BaseModel):
    """Cuerpo opcional al finalizar. Sin columnas en incidente: resumen en bitácora; pagos en otro módulo."""

    diagnostico_final: str | None = Field(
        default=None,
        max_length=2000,
        description="Nota de cierre (opcional; no se persiste en el modelo relacional actual)",
    )
    precio_base: float | None = Field(
        default=None,
        ge=0,
        description="Monto de referencia opcional (informativo)",
    )

    @field_validator("diagnostico_final", mode="before")
    @classmethod
    def strip_diagnostico(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class IncidentRejectResponse(BaseModel):
    ok: bool = True
    message: str = "Rechazo registrado."


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


class IncidenteClienteListItem(BaseModel):
    """Cliente dueño del vehículo asociado al incidente."""

    id: int
    nombre: str = Field(..., description="Nombre completo (nombre y apellido)")
    email: str


class IncidenteVehiculoListItem(BaseModel):
    id: int
    placa: str
    marca_modelo: str = Field(..., description="Marca y modelo concatenados")


class IncidentListItem(BaseModel):
    """Ítem mínimo para listado paginado."""

    id: int
    estado: str
    created_at: datetime | None
    cliente: IncidenteClienteListItem
    vehiculo: IncidenteVehiculoListItem
    evidencias_count: int
    tecnico_id: int | None = Field(default=None, description="Técnico asignado")


class IncidentListResponse(BaseModel):
    items: list[IncidentListItem]
    page: int
    page_size: int
    total: int


MAX_COMENTARIO_CALIFICACION = 500


class CalificacionCreate(BaseModel):
    puntuacion: int = Field(..., ge=1, le=5)
    comentario: str | None = Field(None, max_length=MAX_COMENTARIO_CALIFICACION)

    @field_validator("comentario", mode="before")
    @classmethod
    def strip_optional_comment(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class CalificacionResponse(BaseModel):
    id: int
    incidente_id: int
    puntuacion: int
    comentario: str | None
    fecha: datetime | None
