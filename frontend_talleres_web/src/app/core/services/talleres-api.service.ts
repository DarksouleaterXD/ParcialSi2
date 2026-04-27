import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, forkJoin, map, of, switchMap } from 'rxjs';
import { environment } from '../../../environments/environment';

/** Debe coincidir con `le=100` en `GET /api/admin/talleres` (FastAPI). */
export const TALLERES_ADMIN_MAX_PAGE_SIZE = 100;

export interface TallerListItem {
  id: number;
  nombre: string;
  direccion: string;
  latitud: number | null;
  longitud: number | null;
  telefono: string | null;
  email: string | null;
  horario_atencion: string | null;
  disponibilidad: boolean;
  capacidad_maxima: number;
  calificacion: number;
  id_admin: number;
}

export interface TallerListResponse {
  items: TallerListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TallerCreateBody {
  nombre: string;
  direccion: string;
  latitud: number;
  longitud: number;
  telefono?: string | null;
  email?: string | null;
  capacidad_maxima: number;
  horario_atencion?: string | null;
}

export type TallerUpdateBody = Partial<TallerCreateBody>;

@Injectable({ providedIn: 'root' })
export class TalleresApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  list(opts: {
    page: number;
    pageSize: number;
    q?: string;
    activo?: boolean | null;
  }): Observable<TallerListResponse> {
    let params = new HttpParams().set('page', String(opts.page)).set('page_size', String(opts.pageSize));
    if (opts.q?.trim()) {
      params = params.set('q', opts.q.trim());
    }
    if (opts.activo === true) {
      params = params.set('activo', 'true');
    } else if (opts.activo === false) {
      params = params.set('activo', 'false');
    }
    return this.http.get<TallerListResponse>(`${this.base}/admin/talleres`, { params });
  }

  /**
   * Todos los talleres activos para desplegables. Pagina con `TALLERES_ADMIN_MAX_PAGE_SIZE`
   * (máx. permitido por el backend); si `total` supera una página, pide el resto.
   */
  listAllActivos(): Observable<TallerListItem[]> {
    const pageSize = TALLERES_ADMIN_MAX_PAGE_SIZE;
    return this.list({ page: 1, pageSize, activo: true }).pipe(
      switchMap((first) => {
        if (first.total === 0) {
          return of<TallerListItem[]>([]);
        }
        const pages = Math.max(1, Math.ceil(first.total / pageSize));
        if (pages === 1) {
          return of(first.items);
        }
        return forkJoin(
          Array.from({ length: pages }, (_, i) =>
            this.list({ page: i + 1, pageSize, activo: true }).pipe(map((r) => r.items)),
          ),
        ).pipe(map((rows) => rows.flat()));
      }),
    );
  }

  getById(id: number): Observable<TallerListItem> {
    return this.http.get<TallerListItem>(`${this.base}/admin/talleres/${id}`);
  }

  create(body: TallerCreateBody): Observable<TallerListItem> {
    return this.http.post<TallerListItem>(`${this.base}/admin/talleres`, body);
  }

  update(id: number, body: TallerUpdateBody): Observable<TallerListItem> {
    return this.http.patch<TallerListItem>(`${this.base}/admin/talleres/${id}`, body);
  }

  desactivar(id: number): Observable<TallerListItem> {
    return this.http.post<TallerListItem>(`${this.base}/admin/talleres/${id}/desactivar`, {});
  }

  reactivar(id: number): Observable<TallerListItem> {
    return this.http.post<TallerListItem>(`${this.base}/admin/talleres/${id}/reactivar`, {});
  }
}
