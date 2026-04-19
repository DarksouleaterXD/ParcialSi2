import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  TechnicianListItem,
  TechnicianSpecialty,
  TechniciansApiService,
} from '../../../core/services/technicians-api.service';
import { TallerListItem, TalleresApiService } from '../../../core/services/talleres-api.service';

const SPECIALTY_LABELS: Record<TechnicianSpecialty, string> = {
  battery: 'Batería',
  tires: 'Neumáticos',
  engine: 'Motor',
  general: 'General',
};

@Component({
  selector: 'app-technicians-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './technicians-page.component.html',
})
export class TechniciansPageComponent implements OnInit {
  private readonly techniciansApi = inject(TechniciansApiService);
  private readonly talleresApi = inject(TalleresApiService);
  private readonly fb = inject(FormBuilder);

  readonly talleres = signal<TallerListItem[]>([]);
  readonly items = signal<TechnicianListItem[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly pageSize = 20;
  readonly loading = signal(false);
  readonly loadingTalleres = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly createOpen = signal(false);
  readonly editOpen = signal(false);
  readonly createSubmitting = signal(false);
  readonly editSubmitting = signal(false);
  readonly deactivateId = signal<number | null>(null);

  readonly selectedTallerId = signal<number | null>(null);
  readonly selectedTallerLabel = computed(() => {
    const id = this.selectedTallerId();
    if (id == null) {
      return '';
    }
    const t = this.talleres().find((x) => x.id === id);
    return t ? `${t.nombre} (#${t.id})` : `#${id}`;
  });

  private editingUserId: number | null = null;

  filterForm = this.fb.nonNullable.group({
    tallerId: [null as number | null, Validators.required],
  });

  createForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    apellido: ['', [Validators.required, Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(150)]],
    telefono: ['', [Validators.maxLength(20)]],
    especialidad: ['general' as TechnicianSpecialty, Validators.required],
  });

  editForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    apellido: ['', [Validators.required, Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(150)]],
    telefono: ['', [Validators.maxLength(20)]],
    especialidad: ['general' as TechnicianSpecialty, Validators.required],
  });

  readonly specialtyOptions = (
    Object.entries(SPECIALTY_LABELS) as [TechnicianSpecialty, string][]
  ).map(([value, label]) => ({ value, label }));

  ngOnInit(): void {
    this.loadTalleresOptions();
  }

  specialtyLabel(code: string | null | undefined): string {
    if (!code) {
      return '—';
    }
    return SPECIALTY_LABELS[code as TechnicianSpecialty] ?? code;
  }

  loadTalleresOptions(): void {
    this.loadingTalleres.set(true);
    this.talleresApi.list({ page: 1, pageSize: 200, activo: true }).subscribe({
      next: (r) => {
        this.talleres.set(r.items);
        this.loadingTalleres.set(false);
      },
      error: () => {
        this.loadingTalleres.set(false);
        this.errorMessage.set('No se pudieron cargar los talleres.');
      },
    });
  }

  applyTallerFilter(): void {
    const tid = this.filterForm.controls.tallerId.value;
    if (tid == null || tid <= 0) {
      this.filterForm.controls.tallerId.markAsTouched();
      return;
    }
    this.selectedTallerId.set(tid);
    this.page.set(1);
    this.clearMessages();
    this.loadTechnicians();
  }

  loadTechnicians(): void {
    const tid = this.selectedTallerId();
    if (tid == null) {
      return;
    }
    this.loading.set(true);
    this.errorMessage.set('');
    this.techniciansApi.list(tid, { page: this.page(), pageSize: this.pageSize }).subscribe({
      next: (r) => {
        this.items.set(r.items);
        this.total.set(r.total);
        this.loading.set(false);
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.loading.set(false);
        const d = err?.error?.detail;
        this.errorMessage.set(typeof d === 'string' ? d : 'No se pudieron cargar los técnicos.');
      },
    });
  }

  openCreate(): void {
    this.clearMessages();
    this.createForm.reset({
      nombre: '',
      apellido: '',
      email: '',
      telefono: '',
      especialidad: 'general',
    });
    this.createOpen.set(true);
  }

  closeCreate(): void {
    this.createOpen.set(false);
  }

  submitCreate(): void {
    if (this.createForm.invalid || this.selectedTallerId() == null) {
      this.createForm.markAllAsTouched();
      return;
    }
    const tid = this.selectedTallerId()!;
    const v = this.createForm.getRawValue();
    this.createSubmitting.set(true);
    this.errorMessage.set('');
    this.techniciansApi
      .create(tid, {
        nombre: v.nombre.trim(),
        apellido: v.apellido.trim(),
        email: v.email.trim().toLowerCase(),
        telefono: v.telefono.trim() || null,
        especialidad: v.especialidad,
      })
      .subscribe({
        next: () => {
          this.createSubmitting.set(false);
          this.closeCreate();
          this.successMessage.set(
            'Técnico registrado. Se enviaron credenciales por correo cuando el servidor SMTP está configurado.',
          );
          this.loadTechnicians();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.createSubmitting.set(false);
          const d = err?.error?.detail;
          this.errorMessage.set(typeof d === 'string' ? d : 'No se pudo crear el técnico.');
        },
      });
  }

  openEdit(row: TechnicianListItem): void {
    this.clearMessages();
    this.editingUserId = row.id;
    this.editForm.setValue({
      nombre: row.nombre,
      apellido: row.apellido,
      email: row.email,
      telefono: row.telefono ?? '',
      especialidad: (row.especialidad as TechnicianSpecialty) || 'general',
    });
    this.editOpen.set(true);
  }

  closeEdit(): void {
    this.editOpen.set(false);
    this.editingUserId = null;
  }

  submitEdit(): void {
    if (this.editingUserId == null || this.editForm.invalid || this.selectedTallerId() == null) {
      this.editForm.markAllAsTouched();
      return;
    }
    const tid = this.selectedTallerId()!;
    const v = this.editForm.getRawValue();
    this.editSubmitting.set(true);
    this.errorMessage.set('');
    this.techniciansApi
      .update(tid, this.editingUserId, {
        nombre: v.nombre.trim(),
        apellido: v.apellido.trim(),
        email: v.email.trim().toLowerCase(),
        telefono: v.telefono.trim() || null,
        especialidad: v.especialidad,
      })
      .subscribe({
        next: () => {
          this.editSubmitting.set(false);
          this.closeEdit();
          this.successMessage.set('Técnico actualizado.');
          this.loadTechnicians();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.editSubmitting.set(false);
          const d = err?.error?.detail;
          this.errorMessage.set(typeof d === 'string' ? d : 'No se pudo guardar.');
        },
      });
  }

  confirmDeactivate(row: TechnicianListItem): void {
    const tid = this.selectedTallerId();
    if (tid == null) {
      return;
    }
    this.clearMessages();
    this.deactivateId.set(row.id);
    this.techniciansApi.deactivate(tid, row.id).subscribe({
      next: () => {
        this.deactivateId.set(null);
        this.successMessage.set('Técnico desactivado.');
        this.loadTechnicians();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.deactivateId.set(null);
        const d = err?.error?.detail;
        this.errorMessage.set(typeof d === 'string' ? d : 'No se pudo desactivar.');
      },
    });
  }

  private clearMessages(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
  }
}
