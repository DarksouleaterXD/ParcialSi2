import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { VehiculoDto, VehiculosApiService } from '../../../core/services/vehiculos-api.service';

@Component({
  selector: 'app-vehiculos-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './vehiculos-page.component.html',
})
export class VehiculosPageComponent implements OnInit {
  private readonly api = inject(VehiculosApiService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  items: VehiculoDto[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  loading = false;
  errorMessage = '';
  successMessage = '';

  readonly createOpen = signal(false);
  readonly editOpen = signal(false);
  readonly deleteOpen = signal(false);

  createSubmitting = false;
  editSubmitting = false;
  deleteSubmitting = false;

  private editId: number | null = null;
  vehiculoToDelete: VehiculoDto | null = null;

  filterForm = this.fb.nonNullable.group({
    idUsuario: [0],
  });

  createForm = this.fb.nonNullable.group({
    placa: ['', [Validators.required, Validators.maxLength(20)]],
    marca: ['', [Validators.required, Validators.maxLength(50)]],
    modelo: ['', [Validators.required, Validators.maxLength(50)]],
    anio: [new Date().getFullYear(), [Validators.required, Validators.min(1980), Validators.max(2035)]],
    color: ['', [Validators.maxLength(30)]],
    tipo_seguro: ['', [Validators.maxLength(50)]],
    foto_frontal: ['', [Validators.maxLength(255)]],
    id_usuario: [0],
  });

  editForm = this.fb.nonNullable.group({
    placa: ['', [Validators.required, Validators.maxLength(20)]],
    marca: ['', [Validators.required, Validators.maxLength(50)]],
    modelo: ['', [Validators.required, Validators.maxLength(50)]],
    anio: [2020, [Validators.required, Validators.min(1980), Validators.max(2035)]],
    color: ['', [Validators.maxLength(30)]],
    tipo_seguro: ['', [Validators.maxLength(50)]],
    foto_frontal: ['', [Validators.maxLength(255)]],
    id_usuario: [0],
  });

  ngOnInit(): void {
    this.loadVehiculos();
  }

  isAdmin(): boolean {
    return this.auth.isAdmin();
  }

  loadVehiculos(): void {
    this.loading = true;
    this.errorMessage = '';
    const raw = this.filterForm.getRawValue().idUsuario;
    const idU = typeof raw === 'number' ? raw : Number(raw);
    const idUsuario = this.isAdmin() && !Number.isNaN(idU) && idU > 0 ? idU : undefined;
    this.api.list({ page: this.page, pageSize: this.pageSize, idUsuario }).subscribe({
      next: (r) => {
        this.items = r.items;
        this.total = r.total;
        this.loading = false;
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.loading = false;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudieron cargar los vehículos.';
      },
    });
  }

  applyFilters(): void {
    this.page = 1;
    this.loadVehiculos();
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadVehiculos();
    }
  }

  nextPage(): void {
    if (this.page * this.pageSize < this.total) {
      this.page += 1;
      this.loadVehiculos();
    }
  }

  openCreateModal(): void {
    this.successMessage = '';
    this.createForm.reset({
      placa: '',
      marca: '',
      modelo: '',
      anio: new Date().getFullYear(),
      color: '',
      tipo_seguro: '',
      foto_frontal: '',
      id_usuario: 0,
    });
    this.createOpen.set(true);
  }

  closeCreateModal(): void {
    this.createOpen.set(false);
  }

  saveCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    const v = this.createForm.getRawValue();
    const body: Parameters<VehiculosApiService['create']>[0] = {
      placa: v.placa.trim(),
      marca: v.marca.trim(),
      modelo: v.modelo.trim(),
      anio: v.anio,
      color: v.color.trim() || null,
      tipo_seguro: v.tipo_seguro.trim() || null,
      foto_frontal: v.foto_frontal.trim() || null,
    };
    if (this.isAdmin() && v.id_usuario > 0) {
      body.id_usuario = v.id_usuario;
    }
    this.createSubmitting = true;
    this.errorMessage = '';
    this.api.create(body).subscribe({
      next: () => {
        this.createSubmitting = false;
        this.successMessage = 'Vehículo registrado.';
        this.closeCreateModal();
        this.loadVehiculos();
      },
      error: (err: { error?: { detail?: unknown }; status?: number }) => {
        this.createSubmitting = false;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo registrar el vehículo.';
      },
    });
  }

  openEditModal(row: VehiculoDto): void {
    this.successMessage = '';
    this.editId = row.id;
    this.editForm.reset({
      placa: row.placa,
      marca: row.marca,
      modelo: row.modelo,
      anio: row.anio,
      color: row.color ?? '',
      tipo_seguro: row.tipo_seguro ?? '',
      foto_frontal: row.foto_frontal ?? '',
      id_usuario: row.id_usuario,
    });
    this.editOpen.set(true);
  }

  closeEditModal(): void {
    this.editOpen.set(false);
    this.editId = null;
  }

  saveEdit(): void {
    if (this.editId == null || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const v = this.editForm.getRawValue();
    const body: Record<string, unknown> = {
      placa: v.placa.trim(),
      marca: v.marca.trim(),
      modelo: v.modelo.trim(),
      anio: v.anio,
      color: v.color.trim() || null,
      tipo_seguro: v.tipo_seguro.trim() || null,
      foto_frontal: v.foto_frontal.trim() || null,
    };
    if (this.isAdmin() && v.id_usuario > 0) {
      body['id_usuario'] = v.id_usuario;
    }
    this.editSubmitting = true;
    this.errorMessage = '';
    this.api.update(this.editId, body).subscribe({
      next: () => {
        this.editSubmitting = false;
        this.successMessage = 'Vehículo actualizado.';
        this.closeEditModal();
        this.loadVehiculos();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.editSubmitting = false;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo actualizar el vehículo.';
      },
    });
  }

  openDeleteModal(row: VehiculoDto): void {
    this.successMessage = '';
    this.vehiculoToDelete = row;
    this.deleteOpen.set(true);
  }

  closeDeleteModal(): void {
    this.deleteOpen.set(false);
    this.vehiculoToDelete = null;
  }

  confirmDelete(): void {
    if (!this.vehiculoToDelete) {
      return;
    }
    const id = this.vehiculoToDelete.id;
    this.deleteSubmitting = true;
    this.errorMessage = '';
    this.api.delete(id).subscribe({
      next: () => {
        this.deleteSubmitting = false;
        this.successMessage = 'Vehículo eliminado.';
        this.closeDeleteModal();
        this.loadVehiculos();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.deleteSubmitting = false;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo eliminar el vehículo.';
        this.closeDeleteModal();
      },
    });
  }
}
