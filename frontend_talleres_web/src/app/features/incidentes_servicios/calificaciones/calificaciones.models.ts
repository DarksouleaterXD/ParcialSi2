export interface ClienteResumen {
  id: number;
  nombre: string;
  apellido: string;
  email?: string | null;
}

export interface TallerResumen {
  id: number;
  nombre: string;
}

export interface TecnicoResumen {
  id: number;
  nombre: string;
  apellido: string;
}

export interface ServicioResumen {
  id: number;
  estado: string;
}

export interface IncidenteResumen {
  id: number;
  tipo?: string | null;
  estado: string;
}

export interface PagoResumen {
  id: number;
  monto_total: number;
  estado: string;
}

export interface CalificacionAdminItem {
  id: number;
  servicio_id: number;
  incidente_id: number;
  puntuacion: number;
  comentario?: string | null;
  fecha?: string | null;
  cliente: ClienteResumen;
  taller?: TallerResumen | null;
  tecnico?: TecnicoResumen | null;
  servicio?: ServicioResumen | null;
  incidente?: IncidenteResumen | null;
  pago?: PagoResumen | null;
}

export interface CalificacionSummary {
  promedio_puntuacion: number;
  cantidad_1: number;
  cantidad_2: number;
  cantidad_3: number;
  cantidad_4: number;
  cantidad_5: number;
}

export interface CalificacionAdminResponse {
  items: CalificacionAdminItem[];
  page: number;
  page_size: number;
  total: number;
  summary?: CalificacionSummary | null;
}

export interface CalificacionFilters {
  page?: number;
  page_size?: number;
  cliente?: string;
  taller?: string;
  tecnico?: string;
  puntuacion?: number;
  puntuacion_min?: number;
  puntuacion_max?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  estado_servicio?: string;
}
