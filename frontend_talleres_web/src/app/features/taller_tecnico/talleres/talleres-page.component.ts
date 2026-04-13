import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  TallerListItem,
  TalleresApiService,
} from '../../../core/services/talleres-api.service';

@Component({
  selector: 'app-talleres-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './talleres-page.component.html',
})
export class TalleresPageComponent implements OnInit {
  private readonly api = inject(TalleresApiService);
  private readonly fb = inject(FormBuilder);

  items: TallerListItem[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  loading = false;
  errorMessage = '';
  successMessage = '';
  createModalError = '';
  editModalError = '';

  readonly createOpen = signal(false);
  readonly editOpen = signal(false);

  createSubmitting = false;
  editSubmitting = false;
  estadoSubmittingId: number | null = null;

  private editId: number | null = null;

  filterForm = this.fb.nonNullable.group({
    q: [''],
    estado: ['todos' as 'todos' | 'activo' | 'inactivo'],
  });

  createForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    direccion: ['', [Validators.required, Validators.maxLength(255)]],
    latitud: ['', [Validators.required]],
    longitud: ['', [Validators.required]],
    telefono: ['', [Validators.maxLength(20)]],
    email: ['', [Validators.maxLength(150)]],
    capacidad_maxima: [10, [Validators.required, Validators.min(1), Validators.max(50000)]],
    horario_atencion: ['', [Validators.maxLength(120)]],
  });

  editForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    direccion: ['', [Validators.required, Validators.maxLength(255)]],
    latitud: ['', [Validators.required]],
    longitud: ['', [Validators.required]],
    telefono: ['', [Validators.maxLength(20)]],
    email: ['', [Validators.maxLength(150)]],
    capacidad_maxima: [10, [Validators.required, Validators.min(1), Validators.max(50000)]],
    horario_atencion: ['', [Validators.maxLength(120)]],
  });

  ngOnInit(): void {
    this.loadTalleres();
  }

  loadTalleres(): void {
    this.loading = true;
    this.errorMessage = '';
    const f = this.filterForm.getRawValue();
    let activo: boolean | null = null;
    if (f.estado === 'activo') {
      activo = true;
    } else if (f.estado === 'inactivo') {
      activo = false;
    }
    this.api
      .list({
        page: this.page,
        pageSize: this.pageSize,
        q: f.q || undefined,
        activo,
      })
      .subscribe({
        next: (r) => {
          this.items = r.items;
          this.total = r.total;
          this.loading = false;
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.loading = false;
          const d = err?.error?.detail;
          this.errorMessage = typeof d === 'string' ? d : 'No se pudieron cargar los talleres.';
        },
      });
  }

  applyFilters(): void {
    this.page = 1;
    this.loadTalleres();
  }

  prevPage(): void {
    if (this.page > 1) {
      this.page -= 1;
      this.loadTalleres();
    }
  }

  nextPage(): void {
    if (this.page * this.pageSize < this.total) {
      this.page += 1;
      this.loadTalleres();
    }
  }

  openCreateModal(): void {
    this.successMessage = '';
    this.createModalError = '';
    this.createForm.reset({
      nombre: '',
      direccion: '',
      latitud: '',
      longitud: '',
      telefono: '',
      email: '',
      capacidad_maxima: 10,
      horario_atencion: '',
    });
    this.createOpen.set(true);
  }

  closeCreateModal(): void {
    this.createModalError = '';
    this.createOpen.set(false);
  }

  openEditModal(t: TallerListItem): void {
    this.successMessage = '';
    this.editModalError = '';
    this.editId = t.id;
    this.editForm.setValue({
      nombre: t.nombre,
      direccion: t.direccion,
      latitud: t.latitud != null ? String(t.latitud) : '',
      longitud: t.longitud != null ? String(t.longitud) : '',
      telefono: t.telefono ?? '',
      email: t.email ?? '',
      capacidad_maxima: t.capacidad_maxima,
      horario_atencion: t.horario_atencion ?? '',
    });
    this.editOpen.set(true);
  }

  closeEditModal(): void {
    this.editModalError = '';
    this.editOpen.set(false);
    this.editId = null;
  }

  private buildCreateBody() {
    const v = this.createForm.getRawValue();
    const lat = Number(v.latitud);
    const lon = Number(v.longitud);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      return null;
    }
    return {
      nombre: v.nombre.trim(),
      direccion: v.direccion.trim(),
      latitud: lat,
      longitud: lon,
      telefono: v.telefono?.trim() || null,
      email: v.email?.trim() || null,
      capacidad_maxima: v.capacidad_maxima,
      horario_atencion: v.horario_atencion?.trim() || null,
    };
  }

  saveCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    const body = this.buildCreateBody();
    if (!body) {
      this.createModalError = 'Latitud y longitud deben ser números válidos.';
      return;
    }
    if (body.latitud < -90 || body.latitud > 90 || body.longitud < -180 || body.longitud > 180) {
      this.createModalError = 'Coordenadas fuera de rango (lat -90…90, lon -180…180).';
      return;
    }
    this.createSubmitting = true;
    this.createModalError = '';
    this.api.create(body).subscribe({
      next: () => {
        this.createSubmitting = false;
        this.createOpen.set(false);
        this.successMessage = 'Taller registrado correctamente.';
        this.loadTalleres();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.createSubmitting = false;
        const d = err?.error?.detail;
        this.createModalError = typeof d === 'string' ? d : 'No se pudo crear el taller.';
      },
    });
  }

  saveEdit(): void {
    if (this.editId == null || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const v = this.editForm.getRawValue();
    const lat = Number(v.latitud);
    const lon = Number(v.longitud);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      this.editModalError = 'Latitud y longitud deben ser números válidos.';
      return;
    }
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      this.editModalError = 'Coordenadas fuera de rango (lat -90…90, lon -180…180).';
      return;
    }
    this.editSubmitting = true;
    this.editModalError = '';
    this.api
      .update(this.editId, {
        nombre: v.nombre.trim(),
        direccion: v.direccion.trim(),
        latitud: lat,
        longitud: lon,
        telefono: v.telefono?.trim() || null,
        email: v.email?.trim() || null,
        capacidad_maxima: v.capacidad_maxima,
        horario_atencion: v.horario_atencion?.trim() || null,
      })
      .subscribe({
        next: () => {
          this.editSubmitting = false;
          this.closeEditModal();
          this.successMessage = 'Taller actualizado.';
          this.loadTalleres();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.editSubmitting = false;
          const d = err?.error?.detail;
          this.editModalError = typeof d === 'string' ? d : 'No se pudo guardar.';
        },
      });
  }

  toggleDisponibilidad(t: TallerListItem): void {
    this.estadoSubmittingId = t.id;
    this.errorMessage = '';
    const req = t.disponibilidad ? this.api.desactivar(t.id) : this.api.reactivar(t.id);
    req.subscribe({
      next: () => {
        this.estadoSubmittingId = null;
        this.successMessage = t.disponibilidad ? 'Taller desactivado.' : 'Taller reactivado.';
        this.loadTalleres();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.estadoSubmittingId = null;
        const d = err?.error?.detail;
        this.errorMessage = typeof d === 'string' ? d : 'No se pudo cambiar el estado.';
      },
    });
  }

  gpsResumen(t: TallerListItem): string {
    if (t.latitud == null || t.longitud == null) {
      return '—';
    }
    return `${Number(t.latitud).toFixed(5)}, ${Number(t.longitud).toFixed(5)}`;
  }
}
