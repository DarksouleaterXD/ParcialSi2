import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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
