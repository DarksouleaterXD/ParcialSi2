/** DTOs de autenticación y perfil (login, registro, /auth/me). */
export interface LoginRequest {
  email: string;
  password: string;
}

/** Perfil devuelto por GET/PATCH /auth/me. */
export interface UsuarioPerfilDto {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  telefono: string | null;
  estado?: string | null;
  roles: string[];
  foto_perfil?: string | null;
  fecha_registro?: string | null;
}

export interface ProfilePatchBody {
  nombre?: string;
  apellido?: string;
  telefono?: string | null;
  foto_perfil?: string | null;
}

export interface ChangePasswordBody {
  password_actual: string;
  password_nueva: string;
  password_confirmacion: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  roles: string[];
  redirect_hint: string;
  /** Opcional: perfil extendido (diagrama loginExitoso(token, perfilUsuario)) */
  perfil?: UsuarioPerfilDto;
}

/** Alineado a columnas Usuario: nombre, apellido, email, telefono (+ contraseña en claro hacia el backend). */
export interface RegisterRequest {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  telefono: string | null;
}
