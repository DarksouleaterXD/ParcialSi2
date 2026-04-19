import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface RolDto {
  id: number;
  nombre: string;
  descripcion?: string | null;
  permisos?: string[];
}

export interface UsuarioListItem {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  telefono: string | null;
  estado: string | null;
  roles: string[];
}

export interface UsuarioListResponse {
  items: UsuarioListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface UsuarioCreateResponse {
  id: number;
  email: string;
  password_generada: string;
  roles: string[];
}

@Injectable({ providedIn: 'root' })
export class UsersApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  listUsers(opts: {
    page: number;
    pageSize: number;
    q?: string;
    idRol?: number | null;
  }): Observable<UsuarioListResponse> {
    let params = new HttpParams()
      .set('page', String(opts.page))
      .set('page_size', String(opts.pageSize));
    if (opts.q?.trim()) {
      params = params.set('q', opts.q.trim());
    }
    if (opts.idRol != null && opts.idRol > 0) {
      params = params.set('id_rol', String(opts.idRol));
    }
    return this.http.get<UsuarioListResponse>(`${this.base}/admin/users`, { params });
  }

  roles(): Observable<RolDto[]> {
    return this.http.get<RolDto[]>(`${this.base}/admin/roles`);
  }

  createUser(body: {
    nombre: string;
    apellido: string;
    email: string;
    telefono?: string | null;
    id_rol: number;
    password?: string | null;
    password_confirmacion?: string | null;
  }): Observable<UsuarioCreateResponse> {
    return this.http.post<UsuarioCreateResponse>(`${this.base}/admin/users`, body);
  }

  updateUser(
    id: number,
    body: Partial<{
      nombre: string;
      apellido: string;
      email: string;
      telefono: string | null;
      estado: string | null;
      id_rol: number;
      password_nueva: string | null;
      password_confirmacion: string | null;
    }>,
  ): Observable<UsuarioListItem> {
    return this.http.patch<UsuarioListItem>(`${this.base}/admin/users/${id}`, body);
  }

  deactivateUser(id: number): Observable<void> {
    return this.http
      .delete(`${this.base}/admin/users/${id}`, { responseType: 'text' })
      .pipe(map(() => undefined));
  }

  assignUserRole(userId: number, idRol: number): Observable<UsuarioListItem> {
    return this.http.post<UsuarioListItem>(`${this.base}/admin/users/${userId}/roles`, {
      id_rol: idRol,
    });
  }

  unassignUserRole(userId: number, rolId: number): Observable<void> {
    return this.http
      .delete(`${this.base}/admin/users/${userId}/roles/${rolId}`, { responseType: 'text' })
      .pipe(map(() => undefined));
  }
}
