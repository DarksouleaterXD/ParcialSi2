import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import type {
  AssignmentCandidatesResponseDto,
  IncidentDetailDto,
  IncidentListQuery,
  IncidentListResponseDto,
  IncidentRejectResponseDto,
  IncidentesHealthDto,
} from '../models/incidentes-servicios.dto';

/** Cliente HTTP para `/api/incidentes-servicios` (prefijo vía `environment.apiUrl`). */

@Injectable({ providedIn: 'root' })
export class IncidentesServiciosApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;
  private readonly prefix = `${this.base}/incidentes-servicios`;

  health(): Observable<IncidentesHealthDto> {
    return this.http.get<IncidentesHealthDto>(`${this.prefix}/health`).pipe(
      catchError((err: HttpErrorResponse) => throwError(() => err)),
    );
  }

  getIncident(incidenteId: number): Observable<IncidentDetailDto> {
    return this.http.get<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}`).pipe(
      catchError((err: HttpErrorResponse) => throwError(() => err)),
    );
  }

  /** Alias de listado: mismo contrato que `listIncidentes`. */
  getIncidentes(query: IncidentListQuery = {}): Observable<IncidentListResponseDto> {
    return this.listIncidentes(query);
  }

  /** GET `/incidentes-servicios/incidentes` — JWT; filtros y paginación según backend. */
  listIncidentes(query: IncidentListQuery): Observable<IncidentListResponseDto> {
    let params = new HttpParams();
    if (query.page != null) {
      params = params.set('page', String(query.page));
    }
    if (query.page_size != null) {
      params = params.set('page_size', String(query.page_size));
    }
    if (query.estado != null && query.estado.trim() !== '') {
      params = params.set('estado', query.estado.trim());
    }
    if (query.cliente != null && query.cliente >= 1) {
      params = params.set('cliente', String(query.cliente));
    }
    if (query.cliente_busqueda != null && query.cliente_busqueda.trim() !== '') {
      params = params.set('cliente_busqueda', query.cliente_busqueda.trim());
    }
    if (query.vehiculo_placa != null && query.vehiculo_placa.trim() !== '') {
      params = params.set('vehiculo_placa', query.vehiculo_placa.trim());
    }
    if (query.fecha_desde != null && query.fecha_desde.trim() !== '') {
      params = params.set('fecha_desde', query.fecha_desde.trim());
    }
    if (query.fecha_hasta != null && query.fecha_hasta.trim() !== '') {
      params = params.set('fecha_hasta', query.fecha_hasta.trim());
    }
    return this.http.get<IncidentListResponseDto>(`${this.prefix}/incidentes`, { params }).pipe(
      catchError((err: HttpErrorResponse) => throwError(() => err)),
    );
  }

  /**
   * POST `/incidentes-servicios/incidentes/{id}/aceptar`.
   * Técnico: cuerpo vacío `{}`. Administrador: `{"tecnico_id": n}` obligatorio.
   */
  aceptarIncidente(incidenteId: number, body?: { tecnico_id: number }): Observable<IncidentDetailDto> {
    const payload =
      body != null && typeof body.tecnico_id === 'number' && body.tecnico_id >= 1 ? { tecnico_id: body.tecnico_id } : {};
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/aceptar`, payload)
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  /** POST `/incidentes-servicios/incidentes/{id}/rechazar` — cuerpo vacío. */
  rechazarIncidente(incidenteId: number): Observable<IncidentRejectResponseDto> {
    return this.http
      .post<IncidentRejectResponseDto>(`${this.prefix}/incidentes/${incidenteId}/rechazar`, {})
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  /**
   * Respuesta = incidente (sin `evidencias` en cuerpo); conviene `getIncident` tras mutar.
   * POST cuerpo vacío `{}` siempre.
   */
  marcarEnCamino(incidenteId: number): Observable<IncidentDetailDto> {
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/en-camino`, {})
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  marcarEnProceso(incidenteId: number): Observable<IncidentDetailDto> {
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/en-proceso`, {})
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  marcarFinalizado(incidenteId: number): Observable<IncidentDetailDto> {
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/finalizar`, {})
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  getAsignacionCandidatos(incidenteId: number): Observable<AssignmentCandidatesResponseDto> {
    return this.http
      .get<AssignmentCandidatesResponseDto>(`${this.prefix}/incidentes/${incidenteId}/asignacion/candidatos`)
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  confirmarAsignacion(incidenteId: number, tallerId: number): Observable<IncidentDetailDto> {
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/asignacion/confirmar`, {
        taller_id: tallerId,
      })
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  overrideAsignacion(incidenteId: number, tallerId: number, tecnicoId: number): Observable<IncidentDetailDto> {
    return this.http
      .post<IncidentDetailDto>(`${this.prefix}/incidentes/${incidenteId}/asignacion/override`, {
        taller_id: tallerId,
        tecnico_id: tecnicoId,
      })
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }
}

export function incidentesServiciosErrorMessage(err: unknown): string {
  const e = err as HttpErrorResponse;
  const d = e?.error?.detail;
  if (typeof d === 'string' && d.trim()) {
    return d;
  }
  if (Array.isArray(d)) {
    const parts = d.map((x: { msg?: string }) => (typeof x?.msg === 'string' ? x.msg : '')).filter(Boolean);
    if (parts.length) {
      return parts.join(' ');
    }
  }
  if (e.status === 403) {
    return 'No tenés permiso para esta acción.';
  }
  if (e.status === 404) {
    return 'No se encontró el incidente indicado.';
  }
  if (e.status === 409) {
    const body = e.error as { detail?: unknown } | undefined;
    const d409 = typeof body?.detail === 'string' ? body.detail.trim() : '';
    return d409 || 'Esta solicitud ya no está disponible.';
  }
  if (e.status === 422) {
    return 'Los datos enviados no son válidos.';
  }
  if (e.status === 0) {
    return 'No se pudo conectar con el servidor.';
  }
  if (e.status >= 500) {
    return 'Error del servidor. Intentá de nuevo más tarde.';
  }
  return 'No se pudo completar la solicitud.';
}
