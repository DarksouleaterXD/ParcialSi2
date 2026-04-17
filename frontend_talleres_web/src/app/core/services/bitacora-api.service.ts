import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface BitacoraUsuarioRef {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
}

export interface BitacoraItem {
  id: number;
  id_usuario: number;
  modulo: string;
  accion: string;
  ip_origen: string | null;
  resultado: string | null;
  fecha_hora: string | null;
  usuario: BitacoraUsuarioRef;
}

export interface BitacoraListResponse {
  items: BitacoraItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface BitacoraDetailResponse extends BitacoraItem {}

@Injectable({ providedIn: 'root' })
export class BitacoraApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  listBitacora(opts: {
    page: number;
    pageSize: number;
    fecha?: string;
    modulo?: string;
    usuario?: string;
    accion?: string;
  }): Observable<BitacoraListResponse> {
    let params = new HttpParams().set('page', String(opts.page)).set('page_size', String(opts.pageSize));
    if (opts.fecha?.trim()) {
      params = params.set('fecha', opts.fecha.trim());
    }
    if (opts.modulo?.trim()) {
      params = params.set('modulo', opts.modulo.trim());
    }
    if (opts.usuario?.trim()) {
      params = params.set('usuario', opts.usuario.trim());
    }
    if (opts.accion?.trim()) {
      params = params.set('accion', opts.accion.trim());
    }
    return this.http.get<BitacoraListResponse>(`${this.base}/admin/bitacora`, { params });
  }

  getDetail(id: number): Observable<BitacoraDetailResponse> {
    return this.http.get<BitacoraDetailResponse>(`${this.base}/admin/bitacora/${id}`);
  }
}
