/**
 * Contratos JSON (snake_case) del módulo `incidentes_servicios` en FastAPI.
 */

export interface IncidentesHealthDto {
  modulo: string;
  status: string;
}

export interface EvidenceItemDto {
  id: number;
  incidente_id: number;
  tipo: string;
  url_or_path: string;
  created_at: string | null;
}

/** Subconjunto de `ai_result_json` expuesto en detalle/listado. */
export interface AiIncidentResultDto {
  transcripcion?: string;
  danos_identificados?: string[];
  categoria_incidente?: string;
  resumen_automatico?: string;
  confidence?: number;
}

export interface AssignmentScoreBreakdownDto {
  prioridad: number;
  distancia: number;
  especialidad: number;
  disponibilidad: number;
  eta: number;
}

export interface AssignmentCandidateDto {
  taller_id: number;
  /** Nombre comercial (enriquecido por API). */
  taller_nombre?: string | null;
  tecnico_sugerido_id: number | null;
  rank: number;
  score_total: number;
  breakdown: AssignmentScoreBreakdownDto;
  eta_minutos_estimada?: number | null;
  distancia_km?: number | null;
}

export interface AssignmentCandidatesResponseDto {
  incidente_id: number;
  estado: string;
  candidates: AssignmentCandidateDto[];
  assignment_trace?: Record<string, unknown> | null;
}

export interface IncidentDetailDto {
  id: number;
  cliente_id: number;
  vehiculo_id: number;
  estado: string;
  latitud: number;
  longitud: number;
  descripcion_texto: string | null;
  created_at: string | null;
  evidencias_count: number;
  /** Usuario técnico asignado (CU10); null en bolsa. */
  tecnico_id: number | null;
  /** Stub IA (backend); null hasta enriquecimiento. */
  categoria_ia?: string | null;
  prioridad_ia?: string | null;
  resumen_ia?: string | null;
  confianza_ia?: number | null;
  ai_status?: string | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  prompt_version?: string | null;
  ai_result?: AiIncidentResultDto | null;
  calificacion?: IncidentCalificacionDto | null;
  evidencias: EvidenceItemDto[];
}

export interface IncidentCalificacionDto {
  id: number;
  incidente_id: number;
  puntuacion: number;
  comentario: string | null;
  fecha: string | null;
}

/** Query GET `/incidentes-servicios/incidentes` */
export interface IncidentListQuery {
  page?: number;
  page_size?: number;
  estado?: string;
  /** ID usuario dueño (solo admin en backend). */
  cliente?: number;
  /** Solo admin: búsqueda parcial en nombre, apellido o email del dueño. */
  cliente_busqueda?: string;
  /** Coincidencia parcial en placa del vehículo (sin importar mayúsculas). */
  vehiculo_placa?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}

export interface IncidenteClienteListItemDto {
  id: number;
  nombre: string;
  email: string;
}

export interface IncidenteVehiculoListItemDto {
  id: number;
  placa: string;
  marca_modelo: string;
}

/** Fila de `GET /api/incidentes-servicios/incidentes` (incl. `estado` y `tecnico_id`). */
export interface IncidentListItemDto {
  id: number;
  estado: string;
  created_at: string | null;
  cliente: IncidenteClienteListItemDto;
  vehiculo: IncidenteVehiculoListItemDto;
  evidencias_count: number;
  tecnico_id: number | null;
}

/** Respuesta `POST .../rechazar` (no devuelve el incidente). */
export interface IncidentRejectResponseDto {
  ok: boolean;
  message: string;
}

export interface IncidentListResponseDto {
  items: IncidentListItemDto[];
  page: number;
  page_size: number;
  total: number;
}
