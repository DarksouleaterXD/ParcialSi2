/**
 * Modelos de dominio: listado y detalle (contratos = DTOs del API).
 * Backend: `GET .../incidentes`, `GET .../incidentes/{id}`, aceptar/rechazar.
 */
import type { IncidentDetailDto, IncidentListItemDto } from './incidentes-servicios.dto';

/**
 * Solicitud de servicio (fila de listado).
 * Campos alineados al backend: `estado` (p. ej. Pendiente, Asignado) y `tecnico_id` (null en bolsa).
 */
export type Incidente = IncidentListItemDto;

/** Detalle; incluye `estado`, `tecnico_id`, evidencias y campos de IA. */
export type IncidenteDetalle = IncidentDetailDto;

/** `true` si aún se puede aceptar/rechazar según negocio (Pendiente en bolsa, sin otra lógica aquí). */
export function isEstadoPendiente(estado: string | null | undefined): boolean {
  return (estado ?? '').trim().toLowerCase() === 'pendiente';
}

/** Alinea variantes "En Camino" / "en camino" → `en_camino`. */
export function normalizeEstadoIncidente(estado: string | null | undefined): string {
  return (estado ?? '').trim().toLowerCase().replace(/\s+/g, '_');
}

export function estadoIncidenteBadgeClass(estado: string | null | undefined): string {
  const e = (estado ?? '').trim().toLowerCase();
  if (e === 'pendiente' || e === 'pendiente ia') {
    return 'border-slate-200 bg-slate-100 text-slate-700';
  }
  if (e === 'revision manual') {
    return 'border-amber-200 bg-amber-50 text-amber-950';
  }
  if (e === 'asignado') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }
  if (e === 'en camino' || e === 'en_camino') {
    return 'border-amber-200 bg-amber-50 text-amber-900';
  }
  if (e === 'en proceso' || e === 'en_proceso' || e === 'en curso' || e === 'en_curso') {
    return 'border-blue-200 bg-blue-50 text-blue-900';
  }
  if (e === 'cerrado' || e === 'finalizado' || e === 'resuelto' || e === 'completado') {
    return 'border-indigo-200 bg-indigo-50 text-indigo-900';
  }
  if (e === 'cancelado') {
    return 'border-red-200 bg-red-50 text-red-800';
  }
  return 'border-slate-200 bg-white text-slate-600';
}

export function prioridadIaBadgeClass(prioridad: string | null | undefined): string {
  const p = (prioridad ?? '').trim().toUpperCase();
  if (p === 'CRÍTICA' || p === 'CRITICA') {
    return 'border-red-200 bg-red-50 text-red-800';
  }
  if (p === 'ALTA') {
    return 'border-orange-200 bg-orange-50 text-orange-900';
  }
  if (p === 'MEDIA') {
    return 'border-amber-200 bg-amber-50 text-amber-900';
  }
  if (p === 'BAJA') {
    return 'border-slate-200 bg-slate-100 text-slate-700';
  }
  return 'border-slate-200 bg-white text-slate-500';
}
