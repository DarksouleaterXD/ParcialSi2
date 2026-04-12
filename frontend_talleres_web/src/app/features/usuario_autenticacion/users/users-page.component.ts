import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import {
  RolDto,
  UsuarioListItem,
  UsersApiService,
} from '../../../core/services/users-api.service';

@Component({
  selector: 'app-users-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './users-page.component.html',
})
export class UsersPageComponent implements OnInit {
  private readonly api = inject(UsersApiService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  items: UsuarioListItem[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  roles: RolDto[] = [];
  loading = false;
  errorMessage = '';
  successMessage = '';
  /** Errores de crear/editar usuario mostrados dentro del modal (no en el banner global). */
  createModalError = '';
  editModalError = '';

  readonly createOpen = signal(false);
  readonly editOpen = signal(false);
  readonly deleteOpen = signal(false);

  createSubmitting = false;
  editSubmitting = false;
  deleteSubmitting = false;
  /** Fila en la que se está alternando Activo/Inactivo desde la tabla. */
  toggleSubmittingId: number | null = null;

  private editId: number | null = null;
  userToDelete: UsuarioListItem | null = null;

  filterForm = this.fb.nonNullable.group({
    q: [''],
    idRol: [0],
  });

  createForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    apellido: ['', [Validators.required, Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.maxLength(150)]],
    telefono: ['', [Validators.maxLength(20)]],
    id_rol: [0, [Validators.required, Validators.min(1)]],
    password: ['', [Validators.maxLength(128)]],
    password_confirmacion: ['', [Validators.maxLength(128)]],
  });

  editForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    apellido: ['', [Validators.required, Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.maxLength(150)]],
    telefono: ['', [Validators.maxLength(20)]],
    estado: ['Activo'],
    id_rol: [0, [Validators.required, Validators.min(1)]],
    password_nueva: ['', [Validators.maxLength(128)]],
    password_confirmacion: ['', [Validators.maxLength(128)]],
  });

  ngOnInit(): void {
    this.loadRoles();
    this.loadUsers();
  }

  loadRoles(): void {
    this.api.roles().subscribe({
      next: (r) => {
        this.roles = r;
      },
      error: () => {
        this.errorMessage = 'No se pudieron cargar los roles.';
      },
    });
  }

  loadUsers(): void {
    this.loading = true;
    this.errorMessage = '';
    const f = this.filterForm.getRawValue();
    const idRol = f.idRol > 0 ? f.idRol : null;
    this.api
      .listUsers({
        page: this.page,
        pageSize: this.pageSize,
        q: f.q || undefined,
        idRol: idRol ?? undefined,
      })
      .subscribe({
        next: (res) => {
          this.items = res.items;
          this.total = res.total;
          this.loading = false;
        },
        error: (err) => {
          this.loading = false;
          this.errorMessage = err?.error?.detail ?? 'Error al listar usuarios.';
        },
      });
  }

  applyFilters(): void {
    this.page = 1;
    this.loadUsers();
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadUsers();
    }
  }

  nextPage(): void {
    if (this.page * this.pageSize < this.total) {
      this.page += 1;
      this.loadUsers();
    }
  }

  openCreateModal(): void {
    this.clearMessages();
    this.createModalError = '';
    this.createForm.reset({
      nombre: '',
      apellido: '',
      email: '',
      telefono: '',
      id_rol: this.roles[0]?.id ?? 0,
      password: '',
      password_confirmacion: '',
    });
    this.createOpen.set(true);
  }

  closeCreateModal(): void {
    this.createModalError = '';
    this.createOpen.set(false);
  }

  openEditModal(u: UsuarioListItem): void {
    this.clearMessages();
    this.editModalError = '';
    this.editId = u.id;
    const rol = this.roles.find((r) => u.roles.includes(r.nombre));
    this.editForm.setValue({
      nombre: u.nombre,
      apellido: u.apellido,
      email: u.email,
      telefono: u.telefono ?? '',
      estado: u.estado ?? 'Activo',
      id_rol: rol?.id ?? this.roles[0]?.id ?? 0,
      password_nueva: '',
      password_confirmacion: '',
    });
    this.editOpen.set(true);
  }

  closeEditModal(): void {
    this.editModalError = '';
    this.editOpen.set(false);
    this.editId = null;
  }

  saveCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    const v = this.createForm.getRawValue();
    const pw = v.password.trim();
    const pwc = v.password_confirmacion.trim();
    if (pw || pwc) {
      if (!pw || !pwc) {
        this.createModalError =
          'Completá contraseña y confirmación, o dejá ambas vacías para generar una automática.';
        return;
      }
      if (pw !== pwc) {
        this.createModalError = 'Las contraseñas no coinciden.';
        return;
      }
      const policy = this.passwordPolicyMessage(pw);
      if (policy) {
        this.createModalError = policy;
        return;
      }
    }
    this.createSubmitting = true;
    this.createModalError = '';
    this.errorMessage = '';
    this.api
      .createUser({
        nombre: v.nombre.trim(),
        apellido: v.apellido.trim(),
        email: v.email.trim().toLowerCase(),
        telefono: v.telefono?.trim() || null,
        id_rol: v.id_rol,
        ...(pw ? { password: pw, password_confirmacion: pwc } : {}),
      })
      .subscribe({
        next: (res) => {
          this.createSubmitting = false;
          this.createOpen.set(false);
          this.successMessage = `Usuario creado. Contraseña generada: ${res.password_generada}`;
          this.loadUsers();
        },
        error: (err) => {
          this.createSubmitting = false;
          const detail = err?.error?.detail;
          this.createModalError =
            typeof detail === 'string' ? detail : 'No se pudo crear el usuario.';
        },
      });
  }

  saveEdit(): void {
    if (this.editId == null || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const v = this.editForm.getRawValue();
    const pn = v.password_nueva.trim();
    const pnc = v.password_confirmacion.trim();
    if (pn || pnc) {
      if (!pn || !pnc) {
        this.editModalError =
          'Completá contraseña nueva y confirmación, o dejá ambas vacías para no cambiarla.';
        return;
      }
      if (pn !== pnc) {
        this.editModalError = 'Las contraseñas no coinciden.';
        return;
      }
      const policy = this.passwordPolicyMessage(pn);
      if (policy) {
        this.editModalError = policy;
        return;
      }
    }
    this.editSubmitting = true;
    this.editModalError = '';
    this.errorMessage = '';
    const cambioClave = !!pn;
    this.api
      .updateUser(this.editId, {
        nombre: v.nombre.trim(),
        apellido: v.apellido.trim(),
        email: v.email.trim().toLowerCase(),
        telefono: v.telefono?.trim() || null,
        estado: v.estado,
        id_rol: v.id_rol,
        ...(pn ? { password_nueva: pn, password_confirmacion: pnc } : {}),
      })
      .subscribe({
        next: () => {
          this.editSubmitting = false;
          this.closeEditModal();
          this.successMessage = cambioClave
            ? 'Usuario actualizado; la contraseña fue cambiada.'
            : 'Usuario actualizado.';
          this.loadUsers();
        },
        error: (err) => {
          this.editSubmitting = false;
          const detail = err?.error?.detail;
          this.editModalError = typeof detail === 'string' ? detail : 'No se pudo actualizar.';
        },
      });
  }

  openDeleteModal(u: UsuarioListItem): void {
    this.clearMessages();
    this.userToDelete = u;
    this.deleteOpen.set(true);
  }

  closeDeleteModal(): void {
    this.deleteOpen.set(false);
    this.userToDelete = null;
  }

  /** Alineado a `password_policy_violation` del backend. */
  passwordPolicyMessage(plain: string): string | null {
    if (plain.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres.';
    }
    if (!/[A-Za-z]/.test(plain)) {
      return 'La contraseña debe incluir al menos una letra.';
    }
    if (!/\d/.test(plain)) {
      return 'La contraseña debe incluir al menos un número.';
    }
    return null;
  }

  /** Píldora por rol (mismo patrón que el badge de estado Activo). */
  roleBadgeClasses(roleName: string): string {
    const key = (roleName ?? '').trim().toLowerCase();
    const byRole: Record<string, string> = {
      administrador: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      cliente: 'border-sky-200 bg-sky-50 text-sky-800',
      mecanico: 'border-violet-200 bg-violet-50 text-violet-800',
      mecánico: 'border-violet-200 bg-violet-50 text-violet-800',
    };
    return byRole[key] ?? 'border-amber-200 bg-amber-50 text-amber-900';
  }

  isUsuarioActivo(u: UsuarioListItem): boolean {
    return (u.estado ?? '').trim().toLowerCase() === 'activo';
  }

  isCurrentUser(u: UsuarioListItem): boolean {
    const me = this.auth.profile();
    return me != null && me.id === u.id;
  }

  toggleUsuarioActivo(u: UsuarioListItem): void {
    if (this.isCurrentUser(u)) {
      return;
    }
    const siguiente = this.isUsuarioActivo(u) ? 'Inactivo' : 'Activo';
    this.clearMessages();
    this.toggleSubmittingId = u.id;
    this.api.updateUser(u.id, { estado: siguiente }).subscribe({
      next: () => {
        this.toggleSubmittingId = null;
        this.successMessage =
          siguiente === 'Activo' ? 'Usuario activado.' : 'Usuario desactivado.';
        this.loadUsers();
      },
      error: (err) => {
        this.toggleSubmittingId = null;
        const detail = err?.error?.detail;
        this.errorMessage = typeof detail === 'string' ? detail : 'No se pudo cambiar el estado.';
      },
    });
  }

  confirmDelete(): void {
    if (!this.userToDelete) {
      return;
    }
    this.deleteSubmitting = true;
    this.errorMessage = '';
    this.api.deactivateUser(this.userToDelete.id).subscribe({
      next: () => {
        this.deleteSubmitting = false;
        this.closeDeleteModal();
        this.successMessage = 'Usuario dado de baja.';
        this.loadUsers();
      },
      error: (err) => {
        this.deleteSubmitting = false;
        this.errorMessage = err?.error?.detail ?? 'No se pudo dar de baja.';
      },
    });
  }

  private clearMessages(): void {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
