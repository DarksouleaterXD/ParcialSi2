import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import type { CalificacionAdminResponse, CalificacionFilters, CalificacionAdminItem } from './calificaciones.models';

@Injectable({ providedIn: 'root' })
export class CalificacionesApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;
  private readonly prefix = `${this.base}/admin/incidentes-servicios/calificaciones`;

  listCalificaciones(filters: CalificacionFilters = {}): Observable<CalificacionAdminResponse> {
    let params = new HttpParams();
    if (filters.page != null) {
      params = params.set('page', String(filters.page));
    }
    if (filters.page_size != null) {
      params = params.set('page_size', String(filters.page_size));
    }
    if (filters.cliente && filters.cliente.trim() !== '') {
      params = params.set('cliente', filters.cliente.trim());
    }
    if (filters.taller && filters.taller.trim() !== '') {
      params = params.set('taller', filters.taller.trim());
    }
    if (filters.tecnico && filters.tecnico.trim() !== '') {
      params = params.set('tecnico', filters.tecnico.trim());
    }
    if (filters.puntuacion != null) {
      params = params.set('puntuacion', String(filters.puntuacion));
    }
    if (filters.puntuacion_min != null) {
      params = params.set('puntuacion_min', String(filters.puntuacion_min));
    }
    if (filters.puntuacion_max != null) {
      params = params.set('puntuacion_max', String(filters.puntuacion_max));
    }
    if (filters.fecha_desde && filters.fecha_desde.trim() !== '') {
      params = params.set('fecha_desde', filters.fecha_desde.trim());
    }
    if (filters.fecha_hasta && filters.fecha_hasta.trim() !== '') {
      params = params.set('fecha_hasta', filters.fecha_hasta.trim());
    }
    if (filters.estado_servicio && filters.estado_servicio.trim() !== '') {
      params = params.set('estado_servicio', filters.estado_servicio.trim());
    }
    return this.http
      .get<CalificacionAdminResponse>(this.prefix, { params })
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }

  getCalificacionById(id: number): Observable<CalificacionAdminItem> {
    return this.http
      .get<CalificacionAdminItem>(`${this.prefix}/${id}`)
      .pipe(catchError((err: HttpErrorResponse) => throwError(() => err)));
  }
}

export function calificacionesErrorMessage(err: unknown): string {
  const e = err as HttpErrorResponse;
  const d = e?.error?.detail;
  if (typeof d === 'string' && d.trim()) {
    return d;
  }
  if (e.status === 401) {
    return 'Sesión expirada. Inicia sesión nuevamente.';
  }
  if (e.status === 403) {
    return 'No tienes permisos para consultar calificaciones.';
  }
  if (e.status === 0) {
    return 'No se pudo conectar con el servidor.';
  }
  if (e.status >= 500) {
    return 'Error del servidor. Intentá de nuevo más tarde.';
  }
  return 'No se pudo completar la solicitud.';
}
