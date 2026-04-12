import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  PermisoCatalogoDto,
  RolDetalleDto,
  RolesApiService,
} from '../../../core/services/roles-api.service';

@Component({
  selector: 'app-roles-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './roles-page.component.html',
})
export class RolesPageComponent implements OnInit {
  private readonly api = inject(RolesApiService);
  private readonly fb = inject(FormBuilder);

  items: RolDetalleDto[] = [];
  catalog: PermisoCatalogoDto[] = [];
  loading = false;
  errorMessage = '';
  successMessage = '';

  readonly editOpen = signal(false);
  readonly deleteOpen = signal(false);

  editSubmitting = false;
  deleteSubmitting = false;

  rolToDelete: RolDetalleDto | null = null;
  editingId: number | null = null;

  readonly permEdit = signal<Set<string>>(new Set());

  editForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(50)]],
    descripcion: ['', [Validators.maxLength(255)]],
  });

  ngOnInit(): void {
    this.loadCatalog();
    this.loadRoles();
  }

  loadCatalog(): void {
    this.api.permisosCatalogo().subscribe({
      next: (c) => {
        this.catalog = c;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el catálogo de permisos.';
      },
    });
  }

  loadRoles(): void {
    this.loading = true;
    this.errorMessage = '';
    this.api.listRoles().subscribe({
      next: (rows) => {
        this.items = rows;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err?.error?.detail ?? 'Error al listar roles.';
      },
    });
  }

  toggleEditPerm(codigo: string): void {
    const s = new Set(this.permEdit());
    if (s.has(codigo)) {
      s.delete(codigo);
    } else {
      s.add(codigo);
    }
    this.permEdit.set(s);
  }

  isEditChecked(codigo: string): boolean {
    return this.permEdit().has(codigo);
  }

  openEditModal(r: RolDetalleDto): void {
    this.clearMessages();
    this.editingId = r.id;
    this.editForm.setValue({
      nombre: r.nombre,
      descripcion: r.descripcion ?? '',
    });
    this.permEdit.set(new Set(r.permisos ?? []));
    this.editOpen.set(true);
  }

  closeEditModal(): void {
    this.editOpen.set(false);
    this.editingId = null;
  }

  openDeleteModal(r: RolDetalleDto): void {
    this.clearMessages();
    this.rolToDelete = r;
    this.deleteOpen.set(true);
  }

  closeDeleteModal(): void {
    this.deleteOpen.set(false);
    this.rolToDelete = null;
  }

  selectAllEditPerms(): void {
    this.permEdit.set(new Set(this.catalog.map((p) => p.codigo)));
  }

  clearAllEditPerms(): void {
    this.permEdit.set(new Set());
  }

  saveEdit(): void {
    if (this.editingId == null || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const v = this.editForm.getRawValue();
    this.editSubmitting = true;
    this.errorMessage = '';
    this.api
      .updateRol(this.editingId, {
        nombre: v.nombre.trim(),
        descripcion: v.descripcion.trim() || null,
        permisos: Array.from(this.permEdit()),
      })
      .subscribe({
        next: () => {
          this.editSubmitting = false;
          this.closeEditModal();
          this.successMessage = 'Rol actualizado.';
          this.loadRoles();
        },
        error: (err) => {
          this.editSubmitting = false;
          const d = err?.error?.detail;
          this.errorMessage = typeof d === 'string' ? d : 'No se pudo guardar.';
        },
      });
  }

  confirmDelete(): void {
    if (!this.rolToDelete) {
      return;
    }
    this.deleteSubmitting = true;
    this.errorMessage = '';
    this.api.deleteRol(this.rolToDelete.id).subscribe({
      next: () => {
        this.deleteSubmitting = false;
        this.closeDeleteModal();
        this.successMessage = 'Rol eliminado.';
        this.loadRoles();
      },
      error: (err) => {
        this.deleteSubmitting = false;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo eliminar.';
      },
    });
  }

  permCount(r: RolDetalleDto): number {
    return r.permisos?.length ?? 0;
  }

  /** Texto para tooltip: descripciones según catálogo actual. */
  permTooltip(r: RolDetalleDto): string {
    const map = new Map(this.catalog.map((p) => [p.codigo, p.descripcion]));
    const lines = (r.permisos ?? []).map((c) => map.get(c) ?? c);
    return lines.length ? lines.join('\n') : 'Sin permisos asignados';
  }

  private clearMessages(): void {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
