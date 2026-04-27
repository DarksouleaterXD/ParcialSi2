import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';
import { CalificacionesApiService, calificacionesErrorMessage } from './calificaciones-api.service';
import type { CalificacionAdminItem, CalificacionSummary } from './calificaciones.models';

@Component({
  selector: 'app-calificaciones-admin-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './calificaciones-admin.page.html',
})
export class CalificacionesAdminPage {
  private readonly api = inject(CalificacionesApiService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly error = signal('');
  readonly items = signal<CalificacionAdminItem[]>([]);
  readonly page = signal(1);
  readonly pageSize = signal(10);
  readonly total = signal(0);
  readonly summary = signal<CalificacionSummary | null>(null);
  readonly selected = signal<CalificacionAdminItem | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');

  readonly hasPrev = computed(() => this.page() > 1);
  readonly hasNext = computed(() => this.page() * this.pageSize() < this.total());
  readonly empty = computed(() => !this.loading() && !this.error() && this.items().length === 0);
  readonly total5 = computed(() => this.summary()?.cantidad_5 ?? 0);
  readonly totalLow = computed(() => (this.summary()?.cantidad_1 ?? 0) + (this.summary()?.cantidad_2 ?? 0));
  readonly avg = computed(() => (this.summary()?.promedio_puntuacion ?? 0).toFixed(2));

  readonly estadoOpciones = [
    '',
    'Pendiente',
    'Asignado',
    'En Camino',
    'En Proceso',
    'Finalizado',
    'Pagado',
    'Cancelado',
    'Cerrado',
    'Resuelto',
    'Completado',
  ];

  readonly filtrosForm = this.fb.nonNullable.group({
    cliente: [''],
    taller: [''],
    tecnico: [''],
    puntuacion: [''],
    puntuacion_min: [''],
    puntuacion_max: [''],
    fecha_desde: [''],
    fecha_hasta: [''],
    estado_servicio: [''],
  });

  constructor() {
    this.buscar();
  }

  buscar(): void {
    this.loading.set(true);
    this.error.set('');
    const f = this.filtrosForm.getRawValue();
    const asNum = (v: string): number | undefined => {
      const n = Number(v);
      return Number.isFinite(n) && n >= 1 ? n : undefined;
    };
    this.api
      .listCalificaciones({
        page: this.page(),
        page_size: this.pageSize(),
        cliente: f.cliente,
        taller: f.taller,
        tecnico: f.tecnico,
        puntuacion: asNum(f.puntuacion),
        puntuacion_min: asNum(f.puntuacion_min),
        puntuacion_max: asNum(f.puntuacion_max),
        fecha_desde: f.fecha_desde,
        fecha_hasta: f.fecha_hasta,
        estado_servicio: f.estado_servicio,
      })
      .subscribe({
        next: (res) => {
          this.items.set(res.items ?? []);
          this.total.set(res.total ?? 0);
          this.summary.set(res.summary ?? null);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loading.set(false);
          const e = err as HttpErrorResponse;
          if (e.status === 401) {
            this.auth.clearSessionLocal();
            void this.router.navigateByUrl('/login');
            return;
          }
          this.error.set(calificacionesErrorMessage(err));
        },
      });
  }

  aplicarFiltros(): void {
    this.page.set(1);
    this.buscar();
  }

  limpiarFiltros(): void {
    this.filtrosForm.reset({
      cliente: '',
      taller: '',
      tecnico: '',
      puntuacion: '',
      puntuacion_min: '',
      puntuacion_max: '',
      fecha_desde: '',
      fecha_hasta: '',
      estado_servicio: '',
    });
    this.page.set(1);
    this.buscar();
  }

  prev(): void {
    if (!this.hasPrev()) {
      return;
    }
    this.page.update((p) => p - 1);
    this.buscar();
  }

  next(): void {
    if (!this.hasNext()) {
      return;
    }
    this.page.update((p) => p + 1);
    this.buscar();
  }

  stars(score: number): string {
    const s = Math.max(1, Math.min(5, score || 0));
    return '★★★★★'.slice(0, s) + '☆☆☆☆☆'.slice(0, 5 - s);
  }

  openDetail(item: CalificacionAdminItem): void {
    this.selected.set(item);
    this.detailError.set('');
    this.detailLoading.set(true);
    this.api.getCalificacionById(item.id).subscribe({
      next: (full) => {
        this.selected.set(full);
        this.detailLoading.set(false);
      },
      error: (err: unknown) => {
        this.detailLoading.set(false);
        this.detailError.set(calificacionesErrorMessage(err));
      },
    });
  }

  closeDetail(): void {
    this.selected.set(null);
    this.detailError.set('');
    this.detailLoading.set(false);
  }
}
