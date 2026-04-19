import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type TechnicianSpecialty = 'battery' | 'tires' | 'engine' | 'general';

export interface TechnicianListItem {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  telefono: string | null;
  especialidad: string | null;
  taller_id: number;
  estado: string | null;
}

export interface TechnicianListResponse {
  items: TechnicianListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TechnicianCreateBody {
  nombre: string;
  apellido: string;
  email: string;
  telefono?: string | null;
  especialidad: TechnicianSpecialty;
}

export interface TechnicianCreateResponse extends TechnicianListItem {
  password_generada: string;
}

export type TechnicianUpdateBody = Partial<{
  nombre: string;
  apellido: string;
  email: string;
  telefono: string | null;
  especialidad: TechnicianSpecialty;
}>;

@Injectable({ providedIn: 'root' })
export class TechniciansApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  list(tallerId: number, opts: { page: number; pageSize: number }): Observable<TechnicianListResponse> {
    const params = new HttpParams()
      .set('page', String(opts.page))
      .set('page_size', String(opts.pageSize));
    return this.http.get<TechnicianListResponse>(`${this.base}/admin/talleres/${tallerId}/technicians`, { params });
  }

  create(tallerId: number, body: TechnicianCreateBody): Observable<TechnicianCreateResponse> {
    return this.http.post<TechnicianCreateResponse>(`${this.base}/admin/talleres/${tallerId}/technicians`, body);
  }

  update(tallerId: number, userId: number, body: TechnicianUpdateBody): Observable<TechnicianListItem> {
    return this.http.patch<TechnicianListItem>(`${this.base}/admin/talleres/${tallerId}/technicians/${userId}`, body);
  }

  deactivate(tallerId: number, userId: number): Observable<TechnicianListItem> {
    return this.http.post<TechnicianListItem>(
      `${this.base}/admin/talleres/${tallerId}/technicians/${userId}/desactivar`,
      {},
    );
  }
}
