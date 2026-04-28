"""Schemas Pydantic para análisis IA estructurado (Gemini) y respuestas API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

TipoIncidenteIa = Literal[
    "bateria_descargada",
    "pinchazo",
    "choque",
    "sobrecalentamiento",
    "falla_motor",
    "otro",
]
PrioridadIa = Literal["baja", "media", "alta", "critica"]
EspecialidadIa = Literal[
    "electricidad",
    "llantas",
    "mecanica_general",
    "grua",
    "carroceria",
    "diagnostico",
]


class IncidentStructuredAnalysis(BaseModel):
    """Resultado esperado del modelo (solo JSON, sin markdown)."""

    tipo_incidente: TipoIncidenteIa = "otro"
    prioridad: PrioridadIa = "media"
    especialidad_requerida: EspecialidadIa = "diagnostico"
    resumen_cliente: str = ""
    resumen_taller: str = ""
    recomendaciones_inmediatas: list[str] = Field(default_factory=list)
    riesgos_detectados: list[str] = Field(default_factory=list)
    confianza: float = Field(0.0, ge=0.0, le=1.0)
    requiere_grua: bool = False
    requiere_atencion_inmediata: bool = False

    @field_validator("recomendaciones_inmediatas", "riesgos_detectados", mode="before")
    @classmethod
    def _coerce_str_lists(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()][:40]
        return []

    @field_validator("resumen_cliente", "resumen_taller", mode="before")
    @classmethod
    def _strip_text(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()[:20000]

    @classmethod
    def model_validate_relaxed(cls, data: dict[str, Any]) -> IncidentStructuredAnalysis:
        """Acepta claves con mayúsculas o sinónimos leves; desconocidos → valores seguros."""
        if not isinstance(data, dict):
            raise ValueError("La respuesta IA no es un objeto JSON")
        raw = {str(k).strip(): v for k, v in data.items()}
        tipo = str(raw.get("tipo_incidente") or "otro").strip().lower().replace("-", "_")
        allowed_tipo = {
            "bateria_descargada",
            "pinchazo",
            "choque",
            "sobrecalentamiento",
            "falla_motor",
            "otro",
        }
        if tipo not in allowed_tipo:
            tipo = "otro"
        pr = str(raw.get("prioridad") or "media").strip().lower()
        if pr not in ("baja", "media", "alta", "critica"):
            pr = "media"
        esp = str(raw.get("especialidad_requerida") or "diagnostico").strip().lower()
        allowed_esp = {"electricidad", "llantas", "mecanica_general", "grua", "carroceria", "diagnostico"}
        if esp not in allowed_esp:
            esp = "diagnostico"
        return cls.model_validate(
            {
                "tipo_incidente": tipo,
                "prioridad": pr,
                "especialidad_requerida": esp,
                "resumen_cliente": raw.get("resumen_cliente"),
                "resumen_taller": raw.get("resumen_taller"),
                "recomendaciones_inmediatas": raw.get("recomendaciones_inmediatas"),
                "riesgos_detectados": raw.get("riesgos_detectados"),
                "confianza": raw.get("confianza", raw.get("confidence", 0)),
                "requiere_grua": raw.get("requiere_grua", False),
                "requiere_atencion_inmediata": raw.get("requiere_atencion_inmediata", False),
            },
        )


class IncidentAnalysisRunRequest(BaseModel):
    """Cuerpo opcional: transcripción ya obtenida en otro paso (p. ej. futuro pipeline de audio)."""

    transcripcion_audio: str | None = Field(None, max_length=50000)

    @field_validator("transcripcion_audio", mode="before")
    @classmethod
    def _strip_transcription(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class IncidentAnalysisApiResponse(BaseModel):
    incidente_id: int
    tipo_incidente: str
    prioridad: str
    especialidad_requerida: str
    resumen_cliente: str
    resumen_taller: str
    recomendaciones_inmediatas: list[str]
    riesgos_detectados: list[str]
    confianza: float
    requiere_grua: bool
    requiere_atencion_inmediata: bool
    estado: str | None = Field(default=None, description="Estado del registro persistido: ok, baja_confianza, failed")
    modelo_usado: str | None = None
