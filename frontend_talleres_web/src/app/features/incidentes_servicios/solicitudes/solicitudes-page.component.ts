import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import type { IncidentListItemDto } from '../../../core/models/incidentes-servicios.dto';
import { estadoIncidenteBadgeClass } from '../../../core/models/incidente.model';
import {
  IncidentesServiciosApiService,
  incidentesServiciosErrorMessage,
} from '../../../core/services/incidentes-servicios-api.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-solicitudes-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe, RouterLink],
  templateUrl: './solicitudes-page.component.html',
})
export class SolicitudesPageComponent implements OnInit {
  private readonly api = inject(IncidentesServiciosApiService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly listItems = signal<IncidentListItemDto[]>([]);
  readonly listTotal = signal(0);
  readonly listPage = signal(1);
  readonly listPageSize = signal(10);
  readonly listLoading = signal(false);
  readonly listError = signal('');

  readonly hasPrevListPage = computed(() => this.listPage() > 1);
  readonly hasNextListPage = computed(() => this.listPage() * this.listPageSize() < this.listTotal());
  readonly listEmpty = computed(() => !this.listLoading() && !this.listError() && this.listItems().length === 0);

  readonly estadoFiltroOpciones: { value: string; label: string }[] = [
    { value: '', label: 'Cualquier estado' },
    { value: 'Pendiente', label: 'Pendiente' },
    { value: 'En curso', label: 'En curso' },
    { value: 'Asignado', label: 'Asignado' },
    { value: 'Cerrado', label: 'Cerrado' },
    { value: 'Finalizado', label: 'Finalizado' },
    { value: 'Cancelado', label: 'Cancelado' },
    { value: 'Resuelto', label: 'Resuelto' },
    { value: 'Completado', label: 'Completado' },
  ];

  readonly filterForm = this.fb.nonNullable.group({
    estado: [''],
    clienteTexto: [''],
    vehiculoPlaca: [''],
    fecha_desde: [''],
    fecha_hasta: [''],
  });

  ngOnInit(): void {
    this.loadIncidentList();
  }

  isAdmin(): boolean {
    return this.auth.isAdmin();
  }

  estadoBadgeClass(estado: string | null | undefined): string {
    return estadoIncidenteBadgeClass(estado);
  }

  loadIncidentList(): void {
    const f = this.filterForm.getRawValue();
    const clienteBusqueda =
      this.auth.isAdmin() && f.clienteTexto.trim() !== '' ? f.clienteTexto.trim() : undefined;
    const vehiculoPlaca = f.vehiculoPlaca.trim() !== '' ? f.vehiculoPlaca.trim() : undefined;

    this.listLoading.set(true);
    this.listError.set('');
    this.api
      .getIncidentes({
        page: this.listPage(),
        page_size: this.listPageSize(),
        estado: f.estado.trim() || undefined,
        cliente_busqueda: clienteBusqueda,
        vehiculo_placa: vehiculoPlaca,
        fecha_desde: f.fecha_desde.trim() || undefined,
        fecha_hasta: f.fecha_hasta.trim() || undefined,
      })
      .subscribe({
        next: (res) => {
          this.listItems.set(res.items);
          this.listTotal.set(res.total);
          this.listLoading.set(false);
        },
        error: (err: unknown) => {
          this.listLoading.set(false);
          const e = err as HttpErrorResponse;
          if (e.status === 401) {
            this.auth.clearSessionLocal();
            void this.router.navigateByUrl('/login');
            return;
          }
          // 403/404/5xx: mensaje legible (403 listado: rol sin permiso; 5xx: servidor)
          this.listError.set(incidentesServiciosErrorMessage(err));
        },
      });
  }

  applyListFilters(): void {
    this.listPage.set(1);
    this.loadIncidentList();
  }

  clearListFilters(): void {
    this.filterForm.reset({
      estado: '',
      clienteTexto: '',
      vehiculoPlaca: '',
      fecha_desde: '',
      fecha_hasta: '',
    });
    this.listPage.set(1);
    this.loadIncidentList();
  }

  prevListPage(): void {
    if (this.listPage() > 1) {
      this.listPage.update((p) => p - 1);
      this.loadIncidentList();
    }
  }

  nextListPage(): void {
    if (this.listPage() * this.listPageSize() < this.listTotal()) {
      this.listPage.update((p) => p + 1);
      this.loadIncidentList();
    }
  }
}
