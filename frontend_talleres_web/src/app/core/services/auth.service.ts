import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, delay, map, of, tap, throwError } from 'rxjs';
import {
  ChangePasswordBody,
  LoginRequest,
  LoginResponse,
  ProfilePatchBody,
  RegisterRequest,
  UsuarioPerfilDto,
} from '../../features/usuario_autenticacion/models/auth.dto';
import { environment } from '../../../environments/environment';

const MOCK_DELAY_MS = 900;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly base = environment.apiUrl;

  /** Perfil del usuario autenticado; se carga en el shell tras el login. */
  readonly profile = signal<UsuarioPerfilDto | null>(null);

  login(credentials: LoginRequest): Observable<LoginResponse> {
    if (environment.authMock) {
      return this.loginMock(credentials);
    }
    return this.http
      .post<LoginResponse>(`${this.base}/auth/login`, {
        email: credentials.email.trim().toLowerCase(),
        password: credentials.password,
      })
      .pipe(tap((res) => this.persistSession(res)));
  }

  /**
   * Simulación: JWT ficticio y delay (sin persistir sesión; el componente decide navegación).
   */
  register(payload: RegisterRequest): Observable<LoginResponse> {
    const email = payload.email.trim().toLowerCase();
    const res: LoginResponse = {
      access_token: 'mock.jwt.register.' + btoa(`${email}:${payload.nombre}:${Date.now()}`),
      token_type: 'bearer',
      expires_in: 3600,
      roles: ['Cliente'],
      redirect_hint: 'mobile',
      perfil: {
        id: 0,
        nombre: payload.nombre.trim(),
        apellido: payload.apellido.trim(),
        email,
        telefono: payload.telefono?.trim() ? payload.telefono.trim() : null,
        roles: ['Cliente'],
      },
    };
    return of(res).pipe(delay(MOCK_DELAY_MS));
  }

  private loginMock(credentials: LoginRequest): Observable<LoginResponse> {
    const email = credentials.email.trim().toLowerCase();
    const res: LoginResponse = {
      access_token: 'mock.jwt.' + btoa(`${email}:${Date.now()}`),
      token_type: 'bearer',
      expires_in: 3600,
      roles: ['Administrador'],
      redirect_hint: 'web',
      perfil: {
        id: 1,
        nombre: 'Demo',
        apellido: 'Administrador',
        email,
        telefono: null,
        roles: ['Administrador'],
        foto_perfil: null,
        fecha_registro: new Date().toISOString(),
      },
    };
    return of(res).pipe(
      delay(MOCK_DELAY_MS),
      tap((loginRes) => {
        this.persistSession(loginRes);
        if (loginRes.perfil) {
          this.profile.set(loginRes.perfil);
        }
      }),
    );
  }

  private persistSession(res: LoginResponse): void {
    localStorage.setItem('access_token', res.access_token);
    const roles = Array.isArray(res.roles) ? res.roles : [];
    localStorage.setItem('roles', JSON.stringify(roles));
  }

  /** Lee `roles` del JWT si `localStorage.roles` está ausente o corrupto. */
  private rolesFromAccessToken(): string[] {
    const token = localStorage.getItem('access_token');
    if (!token || token.split('.').length < 2) {
      return [];
    }
    try {
      const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(atob(b64)) as { roles?: unknown };
      return Array.isArray(payload.roles) ? (payload.roles as string[]) : [];
    } catch {
      return [];
    }
  }

  /** GET /auth/me y actualiza `profile`. */
  refreshProfile(): Observable<UsuarioPerfilDto> {
    if (environment.authMock) {
      const raw = localStorage.getItem('roles');
      let roles: string[] = ['Administrador'];
      try {
        if (raw) {
          roles = JSON.parse(raw) as string[];
        }
      } catch {
        /* ignore */
      }
      const p: UsuarioPerfilDto = {
        id: 1,
        nombre: 'Demo',
        apellido: roles.includes('Administrador') ? 'Administrador' : 'Usuario',
        email: 'demo@local',
        telefono: null,
        roles,
        foto_perfil: null,
        fecha_registro: new Date().toISOString(),
      };
      return of(p).pipe(
        delay(150),
        tap((x) => this.profile.set(x)),
      );
    }
    return this.http.get<UsuarioPerfilDto>(`${this.base}/auth/me`).pipe(
      tap((x) => this.profile.set(x)),
      catchError((err) => {
        this.profile.set(null);
        return throwError(() => err);
      }),
    );
  }

  updateMyProfile(body: ProfilePatchBody): Observable<UsuarioPerfilDto> {
    if (environment.authMock) {
      const cur = this.profile();
      const next: UsuarioPerfilDto = {
        ...(cur ?? {
          id: 1,
          nombre: '',
          apellido: '',
          email: 'demo@local',
          telefono: null,
          roles: ['Administrador'],
        }),
        ...body,
        nombre: body.nombre ?? cur?.nombre ?? 'Demo',
        apellido: body.apellido ?? cur?.apellido ?? 'Admin',
        telefono: body.telefono !== undefined ? body.telefono : cur?.telefono ?? null,
        foto_perfil: body.foto_perfil !== undefined ? body.foto_perfil : cur?.foto_perfil,
      };
      return of(next).pipe(delay(300), tap((x) => this.profile.set(x)));
    }
    return this.http.patch<UsuarioPerfilDto>(`${this.base}/auth/me`, body).pipe(tap((x) => this.profile.set(x)));
  }

  changePassword(body: ChangePasswordBody): Observable<void> {
    if (environment.authMock) {
      if (body.password_nueva !== body.password_confirmacion) {
        return throwError(() => ({ error: { detail: 'Las contraseñas nuevas no coinciden.' } }));
      }
      return of(undefined).pipe(delay(400));
    }
    return this.http.post<void>(`${this.base}/auth/me/change-password`, body, { observe: 'response' }).pipe(
      map((res) => {
        if (res.status !== 204) {
          throw new Error('Respuesta inesperada');
        }
        return undefined;
      }),
    );
  }

  logout(): Observable<string> {
    if (environment.authMock) {
      return of('').pipe(
        delay(200),
        tap(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('roles');
          this.profile.set(null);
          void this.router.navigateByUrl('/login');
        }),
      );
    }
    return this.http.post(`${this.base}/auth/logout`, {}, { responseType: 'text' }).pipe(
      tap(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('roles');
        this.profile.set(null);
        void this.router.navigateByUrl('/login');
      }),
    );
  }

  /**
   * Limpia token local y perfil (p. ej. tras 401 del API sin pasar por logout HTTP).
   * La navegación a login la hace quien llama si corresponde.
   */
  clearSessionLocal(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('roles');
    this.profile.set(null);
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('access_token');
  }

  /** Roles efectivos (localStorage o payload JWT). */
  currentRoles(): string[] {
    let roles: string[] = [];
    try {
      const raw = localStorage.getItem('roles');
      roles = raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      roles = [];
    }
    if (!roles.length) {
      roles = this.rolesFromAccessToken();
    }
    return roles;
  }

  isAdmin(): boolean {
    return this.currentRoles().includes('Administrador');
  }

  isTecnico(): boolean {
    return this.currentRoles().includes('Tecnico');
  }

  /**
   * CU10: listado/detalle de solicitudes y aceptación (admin asigna técnico; técnico toma de la bolsa).
   */
  canManageIncidentesCu10(): boolean {
    return this.isAdmin() || this.isTecnico();
  }

  /**
   * @deprecated Preferir `canManageIncidentesCu10()`.
   */
  canManageTallerSolicitudes(): boolean {
    return this.canManageIncidentesCu10();
  }
}
