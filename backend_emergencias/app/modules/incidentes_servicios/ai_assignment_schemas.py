"""Contratos Pydantic para IA multimodal y asignación determinística."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


CategoriaIncidenteIA = Literal["bateria", "llanta", "choque", "motor", "otro"]


class AiIncidentInput(BaseModel):
    """Entrada lógica al motor IA (texto ya sanitizado + rutas de medios)."""

    descripcion_texto: str = ""
    rutas_audio_relativas: list[str] = Field(default_factory=list)
    rutas_imagen_relativas: list[str] = Field(default_factory=list)


class AiIncidentResult(BaseModel):
    """Salida JSON estructurada persistida (subset en columnas legacy + ai_result_json)."""

    transcripcion: str = ""
    danos_identificados: list[str] = Field(default_factory=list)
    categoria_incidente: CategoriaIncidenteIA = "otro"
    resumen_automatico: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("danos_identificados", mode="before")
    @classmethod
    def coerce_danos(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


class AssignmentScoreBreakdown(BaseModel):
    prioridad: float = 0.0
    distancia: float = 0.0
    especialidad: float = 0.0
    disponibilidad: float = 0.0
    eta: float = 0.0


class AssignmentCandidate(BaseModel):
    taller_id: int
    tecnico_sugerido_id: int | None = None
    rank: int = Field(..., ge=1)
    score_total: float
    breakdown: AssignmentScoreBreakdown
    eta_minutos_estimada: float | None = None
    distancia_km: float | None = None


class AssignmentResult(BaseModel):
    incidente_id: int
    candidates: list[AssignmentCandidate]
    weights: dict[str, float]
    trace: dict[str, Any] = Field(default_factory=dict)


class IncidentIaProcessResponse(BaseModel):
    incidente_id: int
    ai_status: str
    estado: str
    skipped: bool = False


class IncidentIaResultResponse(BaseModel):
    incidente_id: int
    ai_status: str | None = None
    estado: str
    ai_provider: str | None = None
    ai_model: str | None = None
    prompt_version: str | None = None
    result: AiIncidentResult | None = None


class AssignmentCandidatesResponse(BaseModel):
    incidente_id: int
    estado: str
    candidates: list[AssignmentCandidate]
    assignment_trace: dict[str, Any] | None = None


class AssignmentConfirmRequest(BaseModel):
    taller_id: int = Field(..., ge=1)


class AssignmentOverrideRequest(BaseModel):
    taller_id: int = Field(..., ge=1)
    tecnico_id: int = Field(..., ge=1)
