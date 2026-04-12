import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface VehiculoDto {
  id: number;
  id_usuario: number;
  placa: string;
  marca: string;
  modelo: string;
  anio: number;
  color: string | null;
  tipo_seguro: string | null;
  foto_frontal: string | null;
  propietario_nombre?: string | null;
  propietario_email?: string | null;
}

export interface VehiculoListResponse {
  items: VehiculoDto[];
  total: number;
  page: number;
  page_size: number;
}

export interface VehiculoCreateBody {
  placa: string;
  marca: string;
  modelo: string;
  anio: number;
  color?: string | null;
  tipo_seguro?: string | null;
  foto_frontal?: string | null;
  id_usuario?: number | null;
}

export type VehiculoUpdateBody = Partial<VehiculoCreateBody>;

@Injectable({ providedIn: 'root' })
export class VehiculosApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  list(opts: { page: number; pageSize: number; idUsuario?: number | null }): Observable<VehiculoListResponse> {
    let params = new HttpParams().set('page', String(opts.page)).set('page_size', String(opts.pageSize));
    if (opts.idUsuario != null && opts.idUsuario > 0) {
      params = params.set('id_usuario', String(opts.idUsuario));
    }
    return this.http.get<VehiculoListResponse>(`${this.base}/vehiculos`, { params });
  }

  create(body: VehiculoCreateBody): Observable<VehiculoDto> {
    return this.http.post<VehiculoDto>(`${this.base}/vehiculos`, body);
  }

  update(id: number, body: VehiculoUpdateBody): Observable<VehiculoDto> {
    return this.http.patch<VehiculoDto>(`${this.base}/vehiculos/${id}`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/vehiculos/${id}`);
  }
}
