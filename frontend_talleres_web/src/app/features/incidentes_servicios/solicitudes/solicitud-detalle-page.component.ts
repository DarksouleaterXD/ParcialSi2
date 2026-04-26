import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import type { AssignmentCandidateDto, IncidentDetailDto } from '../../../core/models/incidentes-servicios.dto';
import {
  IncidentesServiciosApiService,
  incidentesServiciosErrorMessage,
} from '../../../core/services/incidentes-servicios-api.service';
import { AuthService } from '../../../core/services/auth.service';
import {
  estadoIncidenteBadgeClass,
  isEstadoPendiente,
  normalizeEstadoIncidente,
  prioridadIaBadgeClass,
} from '../../../core/models/incidente.model';

@Component({
  selector: 'app-solicitud-detalle-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './solicitud-detalle-page.component.html',
})
export class SolicitudDetallePageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(IncidentesServiciosApiService);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  readonly loading = signal(false);
  readonly errorMessage = signal('');
  readonly detail = signal<IncidentDetailDto | null>(null);
  readonly incidenteId = signal<number | null>(null);
  readonly toastMessage = signal('');
  readonly toastKind = signal<'success' | 'error'>('success');
  readonly actionLoading = signal<
    | 'aceptar'
    | 'rechazar'
    | 'marcarEnCamino'
    | 'marcarEnProceso'
    | 'marcarFinalizado'
    | 'confirmarAsignacion'
    | 'overrideAsignacion'
    | null
  >(null);
  /** Solo administrador: cuerpo JSON `tecnico_id` al aceptar. */
  readonly adminTecnicoIdInput = signal('');

  readonly canManageIncidentesCu10 = computed(() => this.auth.canManageIncidentesCu10());
  readonly isAdminUser = computed(() => this.auth.isAdmin());
  readonly isTecnicoUser = computed(() => this.auth.isTecnico());

  readonly isPendiente = computed(() => {
    const d = this.detail();
    return d != null && isEstadoPendiente(d.estado);
  });

  readonly showAcceptButton = computed(() => this.isPendiente() && this.canManageIncidentesCu10());
  readonly showRejectButton = computed(() => this.isPendiente() && this.isTecnicoUser());

  /** Solo técnico asignado al incidente. */
  readonly canOperateProgreso = computed(() => {
    const d = this.detail();
    if (!d || this.isPendiente()) {
      return false;
    }
    if (!this.isTecnicoUser()) {
      return false;
    }
    const p = this.auth.profile();
    if (p == null || d.tecnico_id == null) {
      return false;
    }
    return d.tecnico_id === p.id;
  });

  readonly estadoKey = computed(() => normalizeEstadoIncidente(this.detail()?.estado));

  readonly showProgresoEnCamino = computed(
    () => this.canOperateProgreso() && this.estadoKey() === 'asignado',
  );
  readonly showProgresoIniciarTrabajo = computed(
    () => this.canOperateProgreso() && this.estadoKey() === 'en_camino',
  );
  readonly showProgresoFinalizar = computed(
    () => this.canOperateProgreso() && this.estadoKey() === 'en_proceso',
  );
  readonly showProgresoPanel = computed(
    () => this.showProgresoEnCamino() || this.showProgresoIniciarTrabajo() || this.showProgresoFinalizar(),
  );

  readonly showAssignedBanner = computed(() => {
    const d = this.detail();
    if (!d || !this.canManageIncidentesCu10() || this.isPendiente()) {
      return false;
    }
    return (d.estado ?? '').trim().toLowerCase() === 'asignado';
  });

  readonly assignedTechnicianLabel = computed(() => {
    const d = this.detail();
    if (!d || !this.showAssignedBanner()) {
      return '';
    }
    const tid = d.tecnico_id;
    if (typeof tid === 'number' && tid >= 1) {
      return `Asignado al técnico ID: ${tid}`;
    }
    return `Estado: ${d.estado}`;
  });

  readonly hasCalificacion = computed(() => {
    const c = this.detail()?.calificacion;
    return !!c && Number.isFinite(c.puntuacion) && c.puntuacion >= 1;
  });

  readonly candidatesLoading = signal(false);
  readonly candidates = signal<AssignmentCandidateDto[]>([]);
  readonly overrideTallerId = signal('');
  readonly overrideTecnicoId = signal('');

  readonly aiStatusNorm = computed(() => (this.detail()?.ai_status ?? '').trim().toLowerCase());

  readonly showIaStructured = computed(() => {
    const d = this.detail();
    return !!d?.ai_result && typeof d.ai_result === 'object';
  });

  readonly showManualReviewBanner = computed(() => this.aiStatusNorm() === 'manual_review');

  readonly showAssignmentAdminPanel = computed(() => {
    if (!this.isAdminUser()) {
      return false;
    }
    const d = this.detail();
    if (!d || d.tecnico_id != null) {
      return false;
    }
    const st = (d.estado ?? '').trim().toLowerCase();
    if (st === 'revision manual') {
      return true;
    }
    return st === 'pendiente' && this.aiStatusNorm() === 'completed';
  });

  readonly canConfirmTopCandidate = computed(() => {
    const d = this.detail();
    if (!d || !this.isAdminUser() || d.tecnico_id != null) {
      return false;
    }
    if ((d.estado ?? '').trim().toLowerCase() !== 'pendiente' || this.aiStatusNorm() !== 'completed') {
      return false;
    }
    return this.candidates().length >= 1;
  });

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    const id = idParam ? Number.parseInt(idParam, 10) : NaN;
    if (!Number.isFinite(id) || id < 1) {
      this.errorMessage.set('ID de incidente no válido.');
      return;
    }
    this.incidenteId.set(id);
    this.load(id);
  }

  prioridadBadgeClass(p: string | null | undefined): string {
    return prioridadIaBadgeClass(p);
  }

  estadoBadgeClass(estado: string | null | undefined): string {
    return estadoIncidenteBadgeClass(estado);
  }

  load(id: number): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.detail.set(null);
    this.adminTecnicoIdInput.set('');
    this.api.getIncident(id).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.loading.set(false);
        this.candidates.set([]);
        if (this.auth.isAdmin()) {
          this.candidatesLoading.set(true);
          this.api.getAsignacionCandidatos(id).subscribe({
            next: (c) => {
              this.candidates.set(c.candidates ?? []);
              this.candidatesLoading.set(false);
            },
            error: () => {
              this.candidates.set([]);
              this.candidatesLoading.set(false);
            },
          });
        }
      },
      error: (err: unknown) => {
        this.loading.set(false);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.errorMessage.set(incidentesServiciosErrorMessage(err));
      },
    });
  }

  retry(): void {
    const id = this.incidenteId();
    if (id != null) {
      this.load(id);
    }
  }

  onAdminTecnicoIdInput(ev: Event): void {
    const el = ev.target as HTMLInputElement;
    this.adminTecnicoIdInput.set(el.value);
  }

  mapsUrl(lat: number, lng: number): string {
    return `https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lng}`)}`;
  }

  estrellasArray(puntuacion: number | null | undefined): number[] {
    const safe = Math.max(0, Math.min(5, Number(puntuacion ?? 0)));
    return Array.from({ length: 5 }, (_, i) => (i < safe ? 1 : 0));
  }

  private showToast(msg: string, kind: 'success' | 'error' = 'success', ms = 4500): void {
    this.toastKind.set(kind);
    this.toastMessage.set(msg);
    window.setTimeout(() => this.toastMessage.set(''), ms);
  }

  aceptarSolicitud(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    this.actionLoading.set('aceptar');
    let body: { tecnico_id: number } | undefined;
    if (this.auth.isAdmin()) {
      const raw = this.adminTecnicoIdInput().trim();
      const tid = Number.parseInt(raw, 10);
      if (!Number.isFinite(tid) || tid < 1) {
        this.actionLoading.set(null);
        this.showToast('Ingresá el ID del técnico a asignar (entero ≥ 1).', 'error');
        return;
      }
      body = { tecnico_id: tid };
    }
    this.api.aceptarIncidente(id, body).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.adminTecnicoIdInput.set('');
        this.actionLoading.set(null);
        this.showToast('Solicitud aceptada correctamente.', 'success');
      },
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        if (e.status === 409) {
          const msg =
            incidentesServiciosErrorMessage(err) || 'Esta solicitud ya fue tomada por otro técnico.';
          this.showToast(msg, 'error');
          this.load(id);
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  rechazarSolicitud(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    if (
      !window.confirm(
        '¿Rechazar esta solicitud? Solo se registra el rechazo en el sistema; el incidente puede seguir pendiente para otros técnicos.',
      )
    ) {
      return;
    }
    this.actionLoading.set('rechazar');
    this.api.rechazarIncidente(id).subscribe({
      next: () => {
        this.actionLoading.set(null);
        void this.router.navigate(['/', 'incidentes', 'solicitudes']);
      },
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        if (e.status === 409) {
          const msg =
            incidentesServiciosErrorMessage(err) || 'Esta solicitud ya fue tomada por otro técnico.';
          this.showToast(msg, 'error');
          this.load(id);
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  private refreshDetailAfterProgress(id: number, successMessage: string): void {
    this.api.getIncident(id).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.actionLoading.set(null);
        this.showToast(successMessage, 'success');
      },
      error: (err: unknown) => {
        this.actionLoading.set(null);
        this.load(id);
        this.showToast(incidentesServiciosErrorMessage(err) || 'Error al recargar el detalle.', 'error');
      },
    });
  }

  marcarEnCamino(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    this.actionLoading.set('marcarEnCamino');
    this.api.marcarEnCamino(id).subscribe({
      next: () => this.refreshDetailAfterProgress(id, 'Listo. Estado: En camino.'),
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  marcarEnProceso(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    this.actionLoading.set('marcarEnProceso');
    this.api.marcarEnProceso(id).subscribe({
      next: () => this.refreshDetailAfterProgress(id, 'Trabajo en curso.'),
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  onOverrideTallerInput(ev: Event): void {
    const el = ev.target as HTMLInputElement;
    this.overrideTallerId.set(el.value);
  }

  onOverrideTecnicoInput(ev: Event): void {
    const el = ev.target as HTMLInputElement;
    this.overrideTecnicoId.set(el.value);
  }

  confirmarMejorCandidato(): void {
    const id = this.incidenteId();
    const top = this.candidates()[0];
    if (id == null || !top || this.actionLoading()) {
      return;
    }
    this.actionLoading.set('confirmarAsignacion');
    this.api.confirmarAsignacion(id, top.taller_id).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.candidates.set([]);
        this.actionLoading.set(null);
        this.showToast('Asignación confirmada.', 'success');
        this.load(id);
      },
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  overrideAsignacionAdmin(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    const tid = Number.parseInt(this.overrideTallerId().trim(), 10);
    const uid = Number.parseInt(this.overrideTecnicoId().trim(), 10);
    if (!Number.isFinite(tid) || tid < 1 || !Number.isFinite(uid) || uid < 1) {
      this.showToast('Ingresá taller ID y técnico ID válidos (enteros ≥ 1).', 'error');
      return;
    }
    this.actionLoading.set('overrideAsignacion');
    this.api.overrideAsignacion(id, tid, uid).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.overrideTallerId.set('');
        this.overrideTecnicoId.set('');
        this.actionLoading.set(null);
        this.showToast('Asignación manual registrada.', 'success');
        this.load(id);
      },
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }

  marcarFinalizado(): void {
    const id = this.incidenteId();
    if (id == null || this.actionLoading()) {
      return;
    }
    this.actionLoading.set('marcarFinalizado');
    this.api.marcarFinalizado(id).subscribe({
      next: () => this.refreshDetailAfterProgress(id, 'Servicio finalizado.'),
      error: (err: unknown) => {
        this.actionLoading.set(null);
        const e = err as HttpErrorResponse;
        if (e.status === 401) {
          this.auth.clearSessionLocal();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.showToast(incidentesServiciosErrorMessage(err), 'error');
      },
    });
  }
}
