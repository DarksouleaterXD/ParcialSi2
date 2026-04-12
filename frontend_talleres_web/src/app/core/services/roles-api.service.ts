import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface RolDetalleDto {
  id: number;
  nombre: string;
  descripcion: string | null;
  permisos: string[];
}

export interface PermisoCatalogoDto {
  codigo: string;
  descripcion: string;
}

export interface RolUpdateBody {
  nombre?: string;
  descripcion?: string | null;
  permisos?: string[];
}

@Injectable({ providedIn: 'root' })
export class RolesApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  listRoles(): Observable<RolDetalleDto[]> {
    return this.http.get<RolDetalleDto[]>(`${this.base}/admin/roles`);
  }

  permisosCatalogo(): Observable<PermisoCatalogoDto[]> {
    return this.http.get<PermisoCatalogoDto[]>(`${this.base}/admin/roles/permisos-catalogo`);
  }

  updateRol(id: number, body: RolUpdateBody): Observable<RolDetalleDto> {
    return this.http.patch<RolDetalleDto>(`${this.base}/admin/roles/${id}`, body);
  }

  deleteRol(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/admin/roles/${id}`);
  }
}
